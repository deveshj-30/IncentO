"""Hindsight Cloud API adapter with bank guards, Reflect schema, and persistent fallback."""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
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
REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_STORE_PATH = REPO_ROOT / ".local" / "hindsight_banks.json"


@dataclass
class StoredMemory:
    id: str
    memory_type: str
    event_time: str
    incident_id: str | None
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


class HindsightAdapter:
    """Adapter for Hindsight Cloud with persistent local simulation for tests and network fallback."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 28.0,
        store_path: Path | None = None,
    ) -> None:
        self.base_url = (
            base_url if base_url is not None else (os.environ.get("HINDSIGHT_BASE_URL") or DEFAULT_BASE_URL)
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else (os.environ.get("HINDSIGHT_API_KEY") or "")
        self.timeout = timeout_seconds
        self.store_path = store_path or LOCAL_STORE_PATH
        self._local_banks: dict[str, dict[str, StoredMemory]] = {}
        self._load_local_store()

    def _load_local_store(self) -> None:
        """Load persistent local bank store if available."""
        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                for bank, items in data.items():
                    self._local_banks[bank] = {k: StoredMemory(**v) for k, v in items.items()}
            except Exception as exc:
                log.warning("Failed to load local hindsight bank store: %s", exc)

    def _save_local_store(self) -> None:
        """Persist local bank store to disk for cross-restart retention."""
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {
                bank: {k: asdict(v) for k, v in items.items()} for bank, items in self._local_banks.items()
            }
            self.store_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("Failed to save local hindsight bank store: %s", exc)

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
        """True if an external Hindsight API key is configured and simulation is not forced."""
        if self.simulation_enabled:
            return False
        return bool(self.api_key and self.api_key.strip())

    @property
    def simulation_enabled(self) -> bool:
        """True if offline simulation mode is explicitly enabled."""
        return os.environ.get("HINDSIGHT_SIMULATE", "").lower() in ("1", "true", "yes")

    def seed_incidents(self, bank_name: str, incidents: list[HistoricalIncident]) -> SeedResult:
        """Seed past historical incidents into memory with scenario isolation."""
        self._validate_bank_name(bank_name)
        if not incidents:
            return SeedResult(status=SeedStatus.SKIPPED)

        # Update local persistent bank
        bank = self._local_banks.setdefault(bank_name, {})
        for inc in incidents:
            for rec in inc.records:
                mem = StoredMemory(
                    id=rec.record_id,
                    memory_type=rec.memory_type.value,
                    event_time=rec.event_time.isoformat(),
                    incident_id=inc.incident_id,
                    summary=rec.summary,
                    metadata={"source": "seed", "incident_title": inc.title},
                )
                bank[rec.record_id] = mem
        self._save_local_store()

        if not self.is_live:
            if self.simulation_enabled:
                return SeedResult(status=SeedStatus.SEEDED)
            return SeedResult(status=SeedStatus.UNAVAILABLE, error="memory_not_configured")

        # Live Hindsight Cloud call
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = []
            for inc in incidents:
                for rec in inc.records:
                    iso_time = rec.event_time.isoformat()
                    payload.append(
                        {
                            "document_id": f"doc-seed-{inc.incident_id}-{rec.record_id}",
                            "content": f"[{inc.title}] {rec.summary}",
                            "timestamp": iso_time,
                            "tags": [
                                f"type:{rec.memory_type.value}",
                                f"time:{iso_time}",
                                f"incident:{inc.incident_id}",
                                f"id:{rec.record_id}",
                            ],
                            "metadata": {
                                "record_id": rec.record_id,
                                "memory_type": rec.memory_type.value,
                                "event_time": iso_time,
                                "incident_id": inc.incident_id,
                            },
                        }
                    )
            with httpx.Client(timeout=self.timeout) as client:
                client.put(f"{self.base_url}/v1/default/banks/{bank_name}", json={}, headers=headers)
                resp = client.post(
                    f"{self.base_url}/v1/default/banks/{bank_name}/memories",
                    json={"items": payload},
                    headers=headers,
                )
                if resp.status_code >= 400:
                    log.warning("Hindsight cloud seed failed: %s %s", resp.status_code, resp.text)
                    return SeedResult(status=SeedStatus.UNAVAILABLE, error="hindsight_api_error")
        except Exception as exc:
            log.warning("Hindsight live seed exception: %s", exc)
            return SeedResult(status=SeedStatus.UNAVAILABLE, error=type(exc).__name__)

        return SeedResult(status=SeedStatus.SEEDED)

    def retain_outcome(self, bank_name: str, outcome: Outcome) -> RetentionResult:
        """Retain a management decision or measured outcome into memory."""
        self._validate_bank_name(bank_name)
        bank = self._local_banks.setdefault(bank_name, {})

        mem_type = (
            RecalledMemoryType.DECISION.value
            if outcome.type == OutcomeType.DECISION
            else RecalledMemoryType.MEASURED_RESULT.value
        )
        iso_time = outcome.event_time.isoformat()
        summary = (
            f"Management decision: {outcome.note}"
            if outcome.type == OutcomeType.DECISION
            else f"Measured outcome: {outcome.note}"
        )

        bank[outcome.outcome_id] = StoredMemory(
            id=outcome.outcome_id,
            memory_type=mem_type,
            event_time=iso_time,
            incident_id=outcome.incident_id,
            summary=summary,
            metadata={"source": "outcome", "type": outcome.type.value},
        )
        self._save_local_store()

        if not self.is_live:
            if self.simulation_enabled:
                return RetentionResult(status=RetentionStatus.RETAINED)
            return RetentionResult(status=RetentionStatus.FAILED, error="memory_not_configured")

        # Live Hindsight Cloud call
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "items": [
                    {
                        "document_id": f"doc-outcome-{outcome.outcome_id}",
                        "content": summary,
                        "timestamp": iso_time,
                        "tags": [
                            f"type:{mem_type}",
                            f"time:{iso_time}",
                            f"incident:{outcome.incident_id}",
                            f"outcome:{outcome.outcome_id}",
                        ],
                        "metadata": {
                            "outcome_id": outcome.outcome_id,
                            "record_type": mem_type,
                            "event_time": iso_time,
                            "incident_id": outcome.incident_id,
                        },
                    }
                ]
            }
            with httpx.Client(timeout=self.timeout) as client:
                client.put(f"{self.base_url}/v1/default/banks/{bank_name}", json={}, headers=headers)
                resp = client.post(
                    f"{self.base_url}/v1/default/banks/{bank_name}/memories",
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

    def _parse_cloud_result(self, item: dict[str, Any], as_of: datetime) -> RecalledMemory | None:
        """Parse a Cloud recall or reflect memory item, dropping undated/future items."""
        meta = item.get("metadata") or {}
        tags = item.get("tags") or []

        # 1. Parse timestamp: require valid timestamp, drop undated items
        ev_time_str = (
            item.get("timestamp")
            or item.get("occurred_start")
            or item.get("mentioned_at")
            or meta.get("event_time")
        )
        if not ev_time_str:
            for t in tags:
                if t.startswith("time:"):
                    ev_time_str = t[5:]
                    break

        if not ev_time_str:
            return None  # Drop results without a timestamp per contract guard

        try:
            ev_time = datetime.fromisoformat(ev_time_str)
            if ev_time.tzinfo is None:
                ev_time = ev_time.replace(tzinfo=UTC)
        except Exception:
            return None

        # Filter strictly by as_of
        if ev_time > as_of:
            return None

        # 2. Parse record / memory type
        type_str = meta.get("memory_type") or meta.get("record_type")
        if not type_str:
            for t in tags:
                if t.startswith("type:"):
                    type_str = t[5:]
                    break

        type_map = {
            "fact": RecalledMemoryType.FACT,
            "hypothesis": RecalledMemoryType.HYPOTHESIS,
            "rejected_hypothesis": RecalledMemoryType.REJECTED_HYPOTHESIS,
            "decision": RecalledMemoryType.DECISION,
            "measured_result": RecalledMemoryType.MEASURED_RESULT,
        }
        mem_type = type_map.get((type_str or "").lower(), RecalledMemoryType.FACT)

        # 3. Parse memory ID: require traceable record ID from metadata, tags, or document_id
        mem_id = meta.get("record_id") or meta.get("outcome_id")
        if not mem_id:
            for t in tags:
                if t.startswith("id:"):
                    mem_id = t[3:]
                    break
                elif t.startswith("outcome:"):
                    mem_id = t[8:]
                    break
        if not mem_id:
            doc_id = item.get("document_id")
            if doc_id and (doc_id.startswith("doc-seed-") or doc_id.startswith("doc-outcome-")):
                mem_id = doc_id.replace("doc-seed-", "").replace("doc-outcome-", "")
        if not mem_id:
            raw_id = item.get("id")
            if raw_id:
                try:
                    uuid.UUID(str(raw_id))
                    is_uuid = True
                except (ValueError, AttributeError):
                    is_uuid = False
                if not is_uuid:
                    mem_id = str(raw_id)

        if not mem_id:
            # Drop untraceable Cloud observations that cannot be traced to a retained record
            return None

        # 4. Parse incident ID
        inc_id = meta.get("incident_id")
        if not inc_id:
            for t in tags:
                if t.startswith("incident:"):
                    inc_id = t[9:]
                    break

        summary = item.get("text") or item.get("content") or ""
        return RecalledMemory(
            id=mem_id,
            memory_type=mem_type,
            event_time=ev_time,
            incident_id=inc_id,
            summary=summary,
        )

    def recall(
        self, bank_name: str, query: str, as_of: datetime | str, limit: int = 5
    ) -> list[RecalledMemory]:
        """Recall relevant memories, strictly enforcing event_time <= as_of."""
        self._validate_bank_name(bank_name)
        if isinstance(as_of, str):
            as_of_dt = datetime.fromisoformat(as_of)
            if as_of_dt.tzinfo is None:
                as_of_dt = as_of_dt.replace(tzinfo=UTC)
        else:
            as_of_dt = as_of

        if self.is_live:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {"query": query, "query_timestamp": as_of_dt.isoformat()}
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/v1/default/banks/{bank_name}/memories/recall",
                        json=payload,
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json().get("results", [])
                        cloud_recalled: list[RecalledMemory] = []
                        for item in data:
                            parsed = self._parse_cloud_result(item, as_of_dt)
                            if parsed:
                                cloud_recalled.append(parsed)
                        return cloud_recalled[:limit]
                    log.warning("Hindsight live recall failed: HTTP %s", resp.status_code)
            except Exception as exc:
                log.warning("Hindsight live recall failed: %s", exc)
            # A configured Cloud that cannot be reached returns nothing. The local simulation store is
            # never a substitute for it: its records would be shown as live memory.
            return []

        # Offline local bank candidates
        bank = self._local_banks.get(bank_name, {})
        candidates: list[RecalledMemory] = []
        for m in bank.values():
            try:
                dt = datetime.fromisoformat(m.event_time)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                if dt <= as_of_dt:
                    type_map = {
                        "fact": RecalledMemoryType.FACT,
                        "hypothesis": RecalledMemoryType.HYPOTHESIS,
                        "rejected_hypothesis": RecalledMemoryType.REJECTED_HYPOTHESIS,
                        "decision": RecalledMemoryType.DECISION,
                        "measured_result": RecalledMemoryType.MEASURED_RESULT,
                    }
                    candidates.append(
                        RecalledMemory(
                            id=m.id,
                            memory_type=type_map.get(m.memory_type, RecalledMemoryType.FACT),
                            event_time=dt,
                            incident_id=m.incident_id,
                            summary=m.summary,
                        )
                    )
            except Exception:
                continue

        candidates.sort(key=lambda m: m.event_time, reverse=True)
        return candidates[:limit]

    def reflect(
        self,
        bank_name: str,
        query: str,
        response_schema: dict[str, Any],
        as_of: datetime | str,
    ) -> tuple[dict[str, Any] | None, list[RecalledMemory]]:
        """Call Hindsight Cloud Reflect with response_schema."""
        self._validate_bank_name(bank_name)
        if not self.is_live:
            return None, []

        if isinstance(as_of, str):
            as_of_dt = datetime.fromisoformat(as_of)
            if as_of_dt.tzinfo is None:
                as_of_dt = as_of_dt.replace(tzinfo=UTC)
        else:
            as_of_dt = as_of

        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "query": query,
                "budget": "low",
                "response_schema": response_schema,
                "include": {"facts": {}},
            }
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/v1/default/banks/{bank_name}/reflect",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code == 200:
                    body = resp.json()
                    st_out = body.get("structured_output")
                    st_err = body.get("structured_output_error")
                    if st_out and not st_err:
                        recalled = []
                        based_on = body.get("based_on", {})
                        for mem in based_on.get("memories", []):
                            parsed = self._parse_cloud_result(mem, as_of_dt)
                            if parsed:
                                recalled.append(parsed)
                        return st_out, recalled
                else:
                    log.warning("Hindsight cloud reflect returned %s: %s", resp.status_code, resp.text)
        except Exception as exc:
            log.warning("Hindsight cloud reflect exception: %s", exc)

        return None, []

    def reset_demo_bank(self, scenario: str) -> ResetResult:
        """Reset a demo memory bank. Refuses any bank not prefixed with incento-demo-."""
        bank_name = f"{DEMO_BANK_PREFIX}{scenario}"
        if not bank_name.startswith(DEMO_BANK_PREFIX):
            return ResetResult(ok=False, error="forbidden_bank_reset")

        self._local_banks.pop(bank_name, None)
        self._save_local_store()

        if self.is_live:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.delete(
                        f"{self.base_url}/v1/default/banks/{bank_name}",
                        headers=headers,
                    )
                    if resp.status_code not in (200, 204, 404):
                        return ResetResult(
                            ok=False,
                            error=f"reset_failed_code_{resp.status_code}",
                        )
            except Exception as exc:
                log.warning("Hindsight cloud reset failed: %s", exc)
                return ResetResult(ok=False, error=type(exc).__name__)

        return ResetResult(ok=True)
