"""Hindsight Cloud API adapter with bank guards and deterministic offline fallback."""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from app.core.schemas import (
    HistoricalIncident,
    Outcome,
    OutcomeType,
    RecalledMemory,
    RecalledMemoryType,
    ResetResult,
    RetentionResult,
    RetentionStatus,
    SeedResult,
    SeedStatus,
)

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.hindsight.vectorize.io"
DEMO_BANK_PREFIX = "incento-demo-"
ALLOWED_PREFIXES = (DEMO_BANK_PREFIX, "incento-")


@dataclass
class StoredMemory:
    id: str
    memory_type: RecalledMemoryType
    event_time: datetime
    incident_id: str | None
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


class HindsightAdapter:
    """Adapter for Hindsight Cloud with local simulation for tests and network fallback."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("HINDSIGHT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or os.environ.get("HINDSIGHT_API_KEY") or ""
        self.timeout = timeout_seconds
        # In-memory store per bank for deterministic local execution and test isolation
        self._local_banks: dict[str, dict[str, StoredMemory]] = {}

    def get_bank_name(self, scenario: str, is_demo: bool = True) -> str:
        """Construct a validated bank name adhering to the prefix rules."""
        prefix = DEMO_BANK_PREFIX if is_demo else "incento-dev-"
        bank = f"{prefix}{scenario}"
        self._validate_bank_name(bank)
        return bank

    def _validate_bank_name(self, bank_name: str) -> None:
        if not any(bank_name.startswith(p) for p in ALLOWED_PREFIXES):
            raise ValueError(
                f"Bank name '{bank_name}' violates isolation rules. "
                f"Must start with one of {ALLOWED_PREFIXES}."
            )

    @property
    def is_live(self) -> bool:
        """True if an external Hindsight API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def seed_incidents(
        self, bank_name: str, incidents: list[HistoricalIncident]
    ) -> SeedResult:
        """Seed past historical incidents into memory."""
        self._validate_bank_name(bank_name)
        if not incidents:
            return SeedResult(status=SeedStatus.SKIPPED)

        bank = self._local_banks.setdefault(bank_name, {})
        for inc in incidents:
            for rec in inc.records:
                mem = StoredMemory(
                    id=rec.record_id,
                    memory_type=rec.memory_type,
                    event_time=rec.event_time,
                    incident_id=inc.incident_id,
                    summary=rec.summary,
                    metadata={"source": "seed", "incident_title": inc.title},
                )
                bank[rec.record_id] = mem

        if self.is_live:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = [
                    {
                        "document_id": rec.record_id,
                        "content": f"[{inc.title}] {rec.summary}",
                        "metadata": {
                            "incident_id": inc.incident_id,
                            "memory_type": rec.memory_type.value,
                            "event_time": rec.event_time.isoformat(),
                        },
                    }
                    for inc in incidents
                    for rec in inc.records
                ]
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/v1/banks/{bank_name}/memories/batch",
                        json={"memories": payload},
                        headers=headers,
                    )
                    if resp.status_code >= 400:
                        log.warning("Hindsight cloud seed failed: %s %s", resp.status_code, resp.text)
            except Exception as exc:
                log.warning("Hindsight live seed failed, kept in local bank: %s", exc)

        return SeedResult(status=SeedStatus.SEEDED)

    def retain_outcome(self, bank_name: str, outcome: Outcome) -> RetentionResult:
        """Retain a management decision or measured outcome into memory."""
        self._validate_bank_name(bank_name)
        bank = self._local_banks.setdefault(bank_name, {})

        mem_type = (
            RecalledMemoryType.DECISION
            if outcome.type == OutcomeType.DECISION
            else RecalledMemoryType.MEASURED_RESULT
        )
        mem_id = f"mem-{outcome.outcome_id}"
        bank[mem_id] = StoredMemory(
            id=mem_id,
            memory_type=mem_type,
            event_time=outcome.event_time,
            incident_id=outcome.incident_id,
            summary=outcome.note,
            metadata={"run_id": outcome.run_id, "type": outcome.type.value},
        )

        if self.is_live:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {
                    "document_id": mem_id,
                    "content": outcome.note,
                    "metadata": {
                        "incident_id": outcome.incident_id,
                        "run_id": outcome.run_id,
                        "type": outcome.type.value,
                        "event_time": outcome.event_time.isoformat(),
                    },
                }
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/v1/banks/{bank_name}/memories",
                        json=payload,
                        headers=headers,
                    )
                    if resp.status_code >= 400:
                        log.warning("Hindsight live retain failed: %s %s", resp.status_code, resp.text)
                        return RetentionResult(status=RetentionStatus.FAILED, error="hindsight_api_error")
            except Exception as exc:
                log.warning("Hindsight live retain exception: %s", exc)
                return RetentionResult(status=RetentionStatus.FAILED, error=type(exc).__name__)

        return RetentionResult(status=RetentionStatus.RETAINED)

    def recall(
        self, bank_name: str, query: str, as_of: datetime, limit: int = 5
    ) -> list[RecalledMemory]:
        """Recall relevant memories, strictly enforcing event_time <= as_of."""
        self._validate_bank_name(bank_name)
        recalled: list[RecalledMemory] = []
        bank = self._local_banks.get(bank_name, {})

        # Temporal filter: reject any memory occurring in the future relative to as_of
        candidates = [m for m in bank.values() if m.event_time <= as_of]

        # In offline simulation, sort by recency or relevance
        candidates.sort(key=lambda m: m.event_time, reverse=True)
        for m in candidates[:limit]:
            recalled.append(
                RecalledMemory(
                    id=m.id,
                    memory_type=m.memory_type,
                    event_time=m.event_time,
                    incident_id=m.incident_id,
                    summary=m.summary,
                )
            )

        if self.is_live:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {"query": query, "limit": limit}
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/v1/banks/{bank_name}/recall",
                        json=payload,
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json().get("memories", [])
                        cloud_recalled: list[RecalledMemory] = []
                        for item in data:
                            meta = item.get("metadata", {})
                            ev_time_raw = meta.get("event_time")
                            ev_time = (
                                datetime.fromisoformat(ev_time_raw)
                                if ev_time_raw
                                else as_of
                            )
                            if ev_time <= as_of:
                                cloud_recalled.append(
                                    RecalledMemory(
                                        id=item.get("document_id") or item.get("id"),
                                        memory_type=RecalledMemoryType(meta.get("memory_type", "fact")),
                                        event_time=ev_time,
                                        incident_id=meta.get("incident_id"),
                                        summary=item.get("content") or item.get("summary", ""),
                                    )
                                )
                        if cloud_recalled:
                            return cloud_recalled
            except Exception as exc:
                log.warning("Hindsight live recall failed, falling back to local: %s", exc)

        return recalled

    def reset_demo_bank(self, scenario: str) -> ResetResult:
        """Reset a demo memory bank. Refuses any bank not prefixed with incento-demo-."""
        bank_name = f"{DEMO_BANK_PREFIX}{scenario}"
        if not bank_name.startswith(DEMO_BANK_PREFIX):
            return ResetResult(ok=False, error="forbidden_bank_reset")

        self._local_banks.pop(bank_name, None)

        if self.is_live:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.delete(
                        f"{self.base_url}/v1/banks/{bank_name}",
                        headers=headers,
                    )
                    if resp.status_code not in (200, 204, 404):
                        return ResetResult(ok=False, error=f"reset_failed_code_{resp.status_code}")
            except Exception as exc:
                log.warning("Hindsight cloud reset failed: %s", exc)
                return ResetResult(ok=False, error=type(exc).__name__)

        return ResetResult(ok=True)
