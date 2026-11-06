"""Run, incident and outcome persistence with idempotency."""

import sqlite3
import threading
from datetime import UTC, datetime

from app.core.schemas import (
    Incident,
    IncidentSummary,
    Investigation,
    InvestigationRequest,
    InvestigationSummary,
    Outcome,
    OutcomeRequest,
    RetentionStatus,
)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def now() -> datetime:
    return datetime.now(UTC)


class IdempotencyConflict(Exception):
    """The same idempotency key was reused with a different request body."""


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.lock = threading.RLock()

    # --- loaded batches ---
    def get_batch(self, scenario: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM loaded_batches WHERE scenario=?", (scenario,)).fetchone()

    def save_batch(self, scenario: str, checksum: str, seed_status: str, seed_error: str | None) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO loaded_batches VALUES (?,?,?,?,?)",
                (scenario, checksum, _iso(now()), seed_status, seed_error),
            )

    # --- investigations ---
    def find_run_by_key(self, key: str) -> tuple[InvestigationRequest, Investigation] | None:
        row = self.conn.execute(
            "SELECT request_json, investigation_json FROM investigations WHERE idempotency_key=?", (key,)
        ).fetchone()
        if row is None:
            return None
        return (
            InvestigationRequest.model_validate_json(row["request_json"]),
            Investigation.model_validate_json(row["investigation_json"]),
        )

    def save_investigation(
        self, request: InvestigationRequest, inv: Investigation, comparison_id: str | None
    ):
        with self.lock, self.conn:
            if inv.incident_id is not None:
                self.conn.execute(
                    "INSERT OR IGNORE INTO incidents VALUES (?,?,?,?,?)",
                    (inv.incident_id, inv.policy_id, comparison_id, inv.scenario, _iso(inv.created_at)),
                )
            self.conn.execute(
                "INSERT INTO investigations VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    inv.run_id,
                    request.idempotency_key,
                    request.model_dump_json(),
                    inv.scenario,
                    inv.policy_id,
                    inv.incident_id,
                    _iso(inv.as_of),
                    inv.memory_mode.value,
                    _iso(inv.created_at),
                    inv.model_dump_json(),
                ),
            )

    def get_investigation(self, run_id: str) -> Investigation | None:
        row = self.conn.execute(
            "SELECT investigation_json FROM investigations WHERE run_id=?", (run_id,)
        ).fetchone()
        return Investigation.model_validate_json(row["investigation_json"]) if row else None

    def list_investigations(self) -> list[InvestigationSummary]:
        rows = self.conn.execute("SELECT investigation_json FROM investigations ORDER BY created_at DESC")
        out = []
        for r in rows:
            inv = Investigation.model_validate_json(r["investigation_json"])
            out.append(
                InvestigationSummary(
                    run_id=inv.run_id,
                    policy_id=inv.policy_id,
                    scenario=inv.scenario,
                    as_of=inv.as_of,
                    created_at=inv.created_at,
                    memory_mode=inv.memory_mode,
                    incident_id=inv.incident_id,
                    flagged=inv.analysis.flagged,
                    memory_status=inv.explanation.memory_status,
                )
            )
        return out

    def next_run_number(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM investigations").fetchone()[0] + 1

    # --- incidents and outcomes ---
    def get_incident(self, incident_id: str) -> Incident | None:
        row = self.conn.execute("SELECT * FROM incidents WHERE incident_id=?", (incident_id,)).fetchone()
        if row is None:
            return None
        runs = [
            r["run_id"]
            for r in self.conn.execute(
                "SELECT run_id FROM investigations WHERE incident_id=? ORDER BY created_at", (incident_id,)
            )
        ]
        return Incident(
            incident_id=row["incident_id"],
            policy_id=row["policy_id"],
            comparison_id=row["comparison_id"],
            scenario=row["scenario"],
            created_at=row["created_at"],
            run_ids=runs,
            outcomes=self.list_outcomes(incident_id),
        )

    def list_incidents(self) -> list[IncidentSummary]:
        out = []
        for r in self.conn.execute("SELECT incident_id FROM incidents ORDER BY created_at DESC"):
            inc = self.get_incident(r["incident_id"])
            out.append(
                IncidentSummary(
                    incident_id=inc.incident_id,
                    policy_id=inc.policy_id,
                    scenario=inc.scenario,
                    run_count=len(inc.run_ids),
                    outcome_count=len(inc.outcomes),
                    pending_retention=any(
                        o.retention_status == RetentionStatus.PENDING for o in inc.outcomes
                    ),
                )
            )
        return out

    def list_outcomes(self, incident_id: str) -> list[Outcome]:
        rows = self.conn.execute(
            "SELECT outcome_json FROM outcomes WHERE incident_id=? ORDER BY event_time, created_at",
            (incident_id,),
        )
        return [Outcome.model_validate_json(r["outcome_json"]) for r in rows]

    def get_outcome(self, outcome_id: str) -> Outcome | None:
        row = self.conn.execute(
            "SELECT outcome_json FROM outcomes WHERE outcome_id=?", (outcome_id,)
        ).fetchone()
        return Outcome.model_validate_json(row["outcome_json"]) if row else None

    def find_outcome_by_key(self, key: str) -> tuple[OutcomeRequest, Outcome] | None:
        row = self.conn.execute(
            "SELECT request_json, outcome_json FROM outcomes WHERE idempotency_key=?", (key,)
        ).fetchone()
        if row is None:
            return None
        return (
            OutcomeRequest.model_validate_json(row["request_json"]),
            Outcome.model_validate_json(row["outcome_json"]),
        )

    def save_outcome(self, request: OutcomeRequest, outcome: Outcome, scenario: str) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO outcomes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    outcome.outcome_id,
                    outcome.incident_id,
                    scenario,
                    outcome.run_id,
                    outcome.idempotency_key,
                    request.model_dump_json(),
                    _iso(outcome.event_time),
                    _iso(outcome.created_at),
                    outcome.retention_status.value,
                    outcome.retention_error,
                    outcome.model_dump_json(),
                ),
            )

    def update_retention(self, outcome: Outcome) -> None:
        with self.lock, self.conn:
            self.conn.execute(
                "UPDATE outcomes SET retention_status=?, retention_error=?, outcome_json=? "
                "WHERE outcome_id=?",
                (
                    outcome.retention_status.value,
                    outcome.retention_error,
                    outcome.model_dump_json(),
                    outcome.outcome_id,
                ),
            )

    def latest_retained_event(self, scenario: str) -> datetime | None:
        row = self.conn.execute(
            "SELECT MAX(event_time) AS t FROM outcomes WHERE scenario=? AND retention_status=?",
            (scenario, RetentionStatus.RETAINED.value),
        ).fetchone()
        return datetime.fromisoformat(row["t"].replace("Z", "+00:00")) if row["t"] else None

    def has_pending_outcome(self, incident_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM outcomes WHERE incident_id=? AND retention_status=? LIMIT 1",
            (incident_id, RetentionStatus.PENDING.value),
        ).fetchone()
        return row is not None

    # --- reset ---
    def clear_scenario(self, scenario: str) -> int:
        with self.lock, self.conn:
            runs = self.conn.execute(
                "SELECT COUNT(*) FROM investigations WHERE scenario=?", (scenario,)
            ).fetchone()[0]
            self.conn.execute("DELETE FROM outcomes WHERE scenario=?", (scenario,))
            self.conn.execute("DELETE FROM investigations WHERE scenario=?", (scenario,))
            self.conn.execute("DELETE FROM incidents WHERE scenario=?", (scenario,))
            self.conn.execute("DELETE FROM loaded_batches WHERE scenario=?", (scenario,))
        return runs


__all__ = ["IdempotencyConflict", "Repository", "now"]
