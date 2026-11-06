#!/usr/bin/env python3
"""Full-flow check against a running API. Usage:

    backend/.venv/bin/python scripts/smoke_test.py [--base-url URL] [--scenario NAME] [--as-of ISO]

Checks health, scenario load (twice, idempotent), policies, a live and an off investigation with the same
analysis digest, idempotent replay, and, when the run produced an incident, the outcome flow. It reports
which modules are still stubs and never counts stub output as a live memory check.
"""

import argparse
import sys
import uuid

import httpx

failures: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(label)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--scenario", default="incentive-risk")
    ap.add_argument("--as-of", default="2026-06-30T23:59:59Z")
    args = ap.parse_args()
    run_tag = uuid.uuid4().hex[:8]
    c = httpx.Client(base_url=args.base_url, timeout=30)

    health = c.get("/api/health")
    if not check(health.status_code == 200, "GET /api/health", health.text[:200]):
        return 1
    h = health.json()
    print(f"      memory_status={h['memory_status']} stubbed_modules={h['stubbed_modules']}")

    first = c.post("/api/demo/load", json={"scenario": args.scenario})
    if not check(first.status_code == 200, "POST /api/demo/load", first.text[:200]):
        return 1
    again = c.post("/api/demo/load", json={"scenario": args.scenario}).json()
    check(again["already_loaded"] is True, "loading the same batch twice is a no-op")
    print(f"      synthetic={first.json()['synthetic']} seed_status={first.json()['seed_status']}")

    policies = [p for p in c.get("/api/policies").json() if p["scenario"] == args.scenario]
    if not check(bool(policies), "GET /api/policies lists the scenario's policy"):
        return 1
    body = {
        "policy_id": policies[0]["policy_id"],
        "scenario": args.scenario,
        "as_of": args.as_of,
        "memory_mode": "live",
        "idempotency_key": f"smoke-live-{run_tag}",
    }
    live = c.post("/api/investigations", json=body)
    if not check(live.status_code in (200, 201), "POST /api/investigations (live)", live.text[:300]):
        return 1
    inv = live.json()
    replay = c.post("/api/investigations", json=body)
    check(replay.status_code == 200 and replay.json()["run_id"] == inv["run_id"], "same key returns the stored run")
    off = c.post(
        "/api/investigations", json={**body, "memory_mode": "off", "idempotency_key": f"smoke-off-{run_tag}"}
    ).json()
    check(off["analysis_digest"] == inv["analysis_digest"], "identical analysis_digest with memory live and off")
    check(c.get(f"/api/investigations/{inv['run_id']}").status_code == 200, "GET /api/investigations/{run_id}")
    check(any(r["run_id"] == inv["run_id"] for r in c.get("/api/investigations").json()), "run appears in the list")
    print(f"      explanation_source={inv['explanation']['explanation_source']} flagged={inv['analysis']['flagged']}")

    incident_id = inv["incident_id"]
    if incident_id is None:
        print("[SKIP] outcome flow: no incident (analysis had insufficient data or is still a stub)")
    else:
        path = f"/api/incidents/{incident_id}/outcomes"
        out_body = {
            "type": "decision",
            "run_id": inv["run_id"],
            "event_time": args.as_of,
            "note": "Smoke test decision",
            "idempotency_key": f"smoke-out-{run_tag}",
        }
        out = c.post(path, json=out_body)
        if check(out.status_code in (200, 201), "POST outcome", out.text[:300]):
            oid = out.json()["outcome_id"]
            print(f"      retention_status={out.json()['retention_status']}")
            check(c.post(path, json=out_body).json()["outcome_id"] == oid, "same outcome key returns the existing outcome")
            incident = c.get(f"/api/incidents/{incident_id}").json()
            check(len(incident["outcomes"]) == 1, "incident lists exactly one outcome")
            if out.json()["retention_status"] != "retained":
                print("      NOTE: outcome not retained; this does not prove live memory")

    print("\nFAILED: " + ", ".join(failures) if failures else "\nSmoke test passed (stubs are not live memory)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
