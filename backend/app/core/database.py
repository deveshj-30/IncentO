"""SQLite connection and run-state schema.

SQLite holds run state only (loaded batches, investigations, incidents, outcomes).
Business records live in fixture files.
"""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS loaded_batches (
    scenario TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    loaded_at TEXT NOT NULL,
    seed_status TEXT NOT NULL,
    seed_error TEXT
);
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    policy_id TEXT NOT NULL,
    comparison_id TEXT NOT NULL,
    scenario TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS investigations (
    run_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    request_json TEXT NOT NULL,
    scenario TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    incident_id TEXT,
    as_of TEXT NOT NULL,
    memory_mode TEXT NOT NULL,
    created_at TEXT NOT NULL,
    investigation_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(incident_id),
    scenario TEXT NOT NULL,
    run_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    request_json TEXT NOT NULL,
    event_time TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retention_status TEXT NOT NULL,
    retention_error TEXT,
    outcome_json TEXT NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
