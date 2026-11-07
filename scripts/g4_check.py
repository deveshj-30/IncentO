#!/usr/bin/env python3
"""G4 persistence checks against a real server process, with no Cloud writes.

    backend/.venv/bin/python scripts/g4_check.py

Starts the API twice on a throwaway SQLite file with simulation memory (HINDSIGHT_SIMULATE=1, empty key), and
checks: outcome saved and retained; same idempotency key returns the same outcome without a duplicate memory
record; a restart keeps the investigation, incident and outcome; a later live run recalls the outcome; an
early ``as_of`` is rejected with 409 as_of_before_memory while memory off still runs; retention retry is
idempotent. The simulation store (.local/hindsight_banks.json) is backed up and restored, so nothing is left
behind. This proves the application loop, not Hindsight Cloud; it never prints as live.

    backend/.venv/bin/python scripts/g4_check.py --cloud

Same checks against Hindsight Cloud (key from backend/.env). It copies the risk fixture under the throwaway
scenario name ``p2dev``, so every write goes to the bank ``incento-demo-p2dev`` and never to
``incento-demo-risk``. It leaves that bank's test records behind.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / ".local" / "hindsight_banks.json"
PORT = 8011
SCENARIO = "risk"
BASE = f"http://127.0.0.1:{PORT}"
failures: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(label)
    return ok


def start(db: str, log: Path, cloud: bool = False, fixtures: str = "") -> subprocess.Popen:
    env = {
        **os.environ,
        **({} if cloud else {"HINDSIGHT_SIMULATE": "1", "HINDSIGHT_API_KEY": ""}),
        **({"FIXTURES_DIR": fixtures} if fixtures else {}),
        "DATABASE_PATH": db,
        "DEMO_RESET_ENABLED": "false",
        "PYTHONPATH": str(ROOT / "backend"),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:create_app", "--factory", "--port", str(PORT)],
        cwd=ROOT / "backend",
        env=env,
        stdout=log.open("a"),
        stderr=subprocess.STDOUT,
    )
    for _ in range(60):
        try:
            if httpx.get(f"{BASE}/api/health", timeout=1).status_code == 200:
                return proc
        except httpx.HTTPError:
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("server did not start; see " + str(log))


def stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    proc.wait(timeout=15)


def main() -> int:
    global SCENARIO
    ap = argparse.ArgumentParser()
    ap.add_argument("--cloud", action="store_true", help="use Hindsight Cloud with the throwaway scenario p2dev")
    cloud = ap.parse_args().cloud
    tmp = Path(tempfile.mkdtemp(prefix="g4-"))
    fixtures = ""
    if cloud:
        SCENARIO = "p2dev"
        (tmp / "fx").mkdir()
        data = json.loads((ROOT / "data" / "scenarios" / "risk.json").read_text())
        data["meta"]["scenario"] = SCENARIO
        (tmp / "fx" / "p2dev.json").write_text(json.dumps(data))
        fixtures = str(tmp / "fx")
    db = str(tmp / "g4.sqlite3")
    log = tmp / "server.log"
    backup = tmp / "banks.json.bak"
    had_store = STORE.exists() and not cloud
    if had_store:
        shutil.copy(STORE, backup)
        STORE.unlink()
    proc = None
    try:
        proc = start(db, log, cloud, fixtures)
        c = httpx.Client(base_url=BASE, timeout=120)
        h = c.get("/api/health").json()
        want = "live" if cloud else "fixture"
        check(h["memory_status"] == want, f"server memory status is {want}", str(h))
        load = c.post("/api/demo/load", json={"scenario": SCENARIO}).json()
        check(load.get("seed_status") == "seeded", f"{SCENARIO} scenario loaded and history seeded", str(load))
        policy = next(p for p in c.get("/api/policies").json() if p["scenario"] == SCENARIO)["policy_id"]

        def run(mode: str, key: str, as_of: str = "2026-11-01T00:00:00Z"):
            return c.post(
                "/api/investigations",
                json={
                    "policy_id": policy,
                    "scenario": SCENARIO,
                    "as_of": as_of,
                    "memory_mode": mode,
                    "idempotency_key": key,
                },
            )

        off = run("off", "g4-off-0001").json()
        live = run("live", "g4-live-0001").json()
        check(off["analysis_digest"] == live["analysis_digest"], "equal analysis_digest, memory off vs live")
        check(
            off["explanation"]["recommendations"][0]["action_type"]
            != live["explanation"]["recommendations"][0]["action_type"],
            "action_type differs between off and live",
        )

        inc = live["incident_id"]
        path = f"/api/incidents/{inc}/outcomes"
        dec = {
            "type": "decision",
            "run_id": live["run_id"],
            "event_time": "2026-11-02T00:00:00Z",
            "note": "Approved one-quarter discount approval pilot.",
            "idempotency_key": "g4-decision-0001",
        }
        res = {
            "type": "measured_result",
            "run_id": live["run_id"],
            "event_time": "2026-11-03T00:00:00Z",
            "note": "Month-end complaint gap fell after the pilot.",
            "idempotency_key": "g4-result-0001",
        }
        d = c.post(path, json=dec)
        r = c.post(path, json=res)
        check(d.status_code == 201 and r.status_code == 201, "decision and measured result saved")
        check(
            d.json()["type"] != r.json()["type"] and d.json()["outcome_id"] != r.json()["outcome_id"],
            "stored as distinct records",
        )
        check(
            d.json()["retention_status"] == "retained" and r.json()["retention_status"] == "retained",
            "both retained",
            f"{d.json()['retention_status']}/{r.json()['retention_status']}",
        )
        again = c.post(path, json=dec)
        check(
            again.status_code == 200 and again.json()["outcome_id"] == d.json()["outcome_id"],
            "same idempotency key returns the same outcome",
        )
        check(len(c.get(f"/api/incidents/{inc}").json()["outcomes"]) == 2, "no duplicate outcome after replay")
        ids = [d.json()["outcome_id"], r.json()["outcome_id"]]
        if not cloud:
            store = json.loads(STORE.read_text()) if STORE.exists() else {}
            bank = next((v for k, v in store.items() if SCENARIO in k), {})
            check(all(i in bank for i in ids), "both outcomes present once in the memory store", str(list(bank)))
        retry = c.post(f"/api/outcomes/{d.json()['outcome_id']}/retention").json()
        check(retry["retention_status"] == "retained", "retention retry on a retained outcome is a no-op")
        check(c.post("/api/outcomes/missing/retention").status_code == 404, "retention retry on unknown id is 404")

        early = run("live", "g4-early-0001", as_of="2026-10-01T00:00:00Z")
        check(
            early.status_code == 409 and early.json().get("code") == "as_of_before_memory",
            "live run before a saved outcome is 409 as_of_before_memory",
            early.text[:200],
        )
        e_off = run("off", "g4-early-0002", as_of="2026-10-01T00:00:00Z")
        check(e_off.status_code == 201, "memory off at the early as_of still runs")

        stop(proc)
        proc = start(db, log, cloud, fixtures)
        c = httpx.Client(base_url=BASE, timeout=120)
        check(c.get(f"/api/investigations/{live['run_id']}").status_code == 200, "after restart: saved run opens")
        check(
            c.get(f"/api/investigations/{live['run_id']}").json()["analysis_digest"] == live["analysis_digest"],
            "after restart: digest unchanged",
        )
        inc_after = c.get(f"/api/incidents/{inc}").json()
        check(
            {o["outcome_id"] for o in inc_after["outcomes"]} == set(ids),
            "after restart: incident still lists both outcomes",
        )
        recalled: set[str] = set()
        ok = False
        for attempt in range(1, 9 if cloud else 2):  # Cloud may index a retained record a little later
            later = c.post(
                "/api/investigations",
                json={
                    "policy_id": policy,
                    "scenario": SCENARIO,
                    "as_of": "2026-11-05T00:00:00Z",
                    "memory_mode": "live",
                    "idempotency_key": f"g4-later-{attempt:04d}",
                },
            )
            ok = later.status_code == 201
            if ok:
                recalled = {m["id"] for m in later.json()["explanation"]["recalled"]}
                if set(ids) <= recalled:
                    break
            time.sleep(10)
        check(ok, "after restart: later live run succeeds", later.text[:200])
        if ok:
            print(f"      explanation_source={later.json()['explanation']['explanation_source']} memory_status={later.json()['explanation']['memory_status']} attempts={attempt}")
            check(set(ids) <= recalled, "after restart: later run recalls both saved outcomes", str(sorted(recalled)))
    finally:
        if proc is not None and proc.poll() is None:
            stop(proc)
        if STORE.exists():
            STORE.unlink()
        if had_store:
            shutil.copy(backup, STORE)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nFAILED: " + ", ".join(failures) if failures else "\nG4 application checks passed (" + ("Hindsight Cloud, throwaway bank incento-demo-p2dev" if cloud else "simulation memory, not Cloud") + ")")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
