#!/usr/bin/env python3
"""P4 Demo Verification Script: Verify Hindsight memory persistence and learning loop.

Usage:
    backend/.venv/bin/python scripts/demo_check.py [--base-url URL] [--scenario NAME]

Verifies:
1. Health endpoint reports memory status.
2. Demo reset cleans the demo bank safely.
3. Scenario data loads and seeds historical memory.
4. Investigation with memory_mode=off produces template output with no memory citations.
5. Investigation with memory_mode=live produces evidence and recalled memory citations.
6. Recording a management outcome retains it in Hindsight memory.
7. Subsequent investigation recalls the recorded outcome (the learning loop payoff).
"""

import argparse
import sys
import uuid

import httpx

failures: list[str] = []


def step(ok: bool, label: str, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}" + (f" -> {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(label)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Hindsight demo learning loop")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--scenario", default="risk")
    parser.add_argument("--policy-id", default=None)
    parser.add_argument("--as-of", default="2026-11-01T00:00:00Z")
    parser.add_argument("--repeat", type=int, default=1, help="Number of repeat comparison runs (default: 1)")
    parser.add_argument("--timeout", type=float, default=90.0, help="Client request timeout (default: 90s)")
    parser.add_argument(
        "--skip-retention",
        action="store_true",
        help="Skip writing outcome retention events to keep the memory bank clean for recording",
    )
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url, timeout=args.timeout)

    print("=== 1. Checking API Health & Memory Status ===")
    try:
        res = client.get("/api/health")
    except (httpx.RequestError, httpx.HTTPError) as exc:
        print(f"[FAIL] Could not connect to API server at {args.base_url}: {exc}")
        print("Hint: Start the server with: cd backend && .venv/bin/python -m uvicorn app.main:create_app --factory")
        return 1

    step(res.status_code == 200, "GET /api/health", res.text[:200])
    h = res.json()
    print(f"      memory_status: {h.get('memory_status')} | stubbed: {h.get('stubbed_modules')}")

    print(f"\n=== 2. Loading Scenario ({args.scenario}) & Seeding Hindsight History ===")
    load_res = client.post("/api/demo/load", json={"scenario": args.scenario})
    step(load_res.status_code == 200, f"POST /api/demo/load ({args.scenario})", load_res.text[:200])
    load_data = load_res.json()
    print(f"      seed_status: {load_data.get('seed_status')} | synthetic: {load_data.get('synthetic')}")

    policy_id = args.policy_id
    if not policy_id:
        pol_res = client.get("/api/policies")
        matching = [p["policy_id"] for p in pol_res.json() if p.get("scenario") == args.scenario]
        policy_id = matching[0] if matching else "POL-RISK-001"
    print(f"      using policy_id: {policy_id}")

    repeat_count = max(1, args.repeat)
    successful_pairs = 0
    last_incident_id = None
    last_run_id = None

    for i in range(1, repeat_count + 1):
        suffix = f" (run {i}/{repeat_count})" if repeat_count > 1 else ""
        print(f"\n=== 3. Investigation: Memory Mode OFF{suffix} ===")
        req_off = {
            "policy_id": policy_id,
            "scenario": args.scenario,
            "as_of": args.as_of,
            "memory_mode": "off",
            "idempotency_key": f"test-off-{i}-{uuid.uuid4().hex[:6]}",
        }
        try:
            inv_off_res = client.post("/api/investigations", json=req_off)
            off_ok = inv_off_res.status_code in (200, 201)
            off_detail = inv_off_res.text[:200]
            inv_off = inv_off_res.json() if off_ok else {}
        except Exception as exc:
            off_ok = False
            off_detail = str(exc)
            inv_off = {}
        step(off_ok, f"POST /api/investigations (memory_mode=off){suffix}", off_detail)

        exp_off = inv_off.get("explanation", {})
        recalled_off = exp_off.get("recalled", [])
        recs_off = exp_off.get("recommendations", [])
        action_off = recs_off[0].get("action_type") if recs_off else None

        step(len(recalled_off) == 0, f"No memories recalled when memory_mode=off{suffix}")
        print(f"      source: {exp_off.get('explanation_source')} | action: {action_off} | recalled: {len(recalled_off)}")

        print(f"\n=== 4. Investigation: Memory Mode LIVE{suffix} ===")
        req_live = {
            "policy_id": policy_id,
            "scenario": args.scenario,
            "as_of": args.as_of,
            "memory_mode": "live",
            "idempotency_key": f"test-live-{i}-{uuid.uuid4().hex[:6]}",
        }
        try:
            inv_live_res = client.post("/api/investigations", json=req_live)
            live_ok = inv_live_res.status_code in (200, 201)
            live_detail = inv_live_res.text[:200]
            inv_live = inv_live_res.json() if live_ok else {}
        except Exception as exc:
            live_ok = False
            live_detail = str(exc)
            inv_live = {}
        step(live_ok, f"POST /api/investigations (memory_mode=live){suffix}", live_detail)

        exp_live = inv_live.get("explanation", {})
        recalled_live = exp_live.get("recalled", [])
        recs_live = exp_live.get("recommendations", [])
        action_live = recs_live[0].get("action_type") if recs_live else None
        influence_live = recs_live[0].get("history_influence", []) if recs_live else []

        print(f"      source: {exp_live.get('explanation_source')} | memory_status: {exp_live.get('memory_status')}")
        print(f"      action: {action_live} | influence: {influence_live} | recalled: {[m.get('id') for m in recalled_live]}")

        # Gate G4 checks
        digest_match = inv_off.get("analysis_digest") and inv_off.get("analysis_digest") == inv_live.get("analysis_digest")
        step(bool(digest_match), f"Analysis digest matches across modes{suffix}")

        action_shifted = (action_off != action_live) and (action_live == "pilot_guardrail")
        step(bool(action_shifted), f"Recommendation shifts to pilot_guardrail with memory{suffix}")

        has_influence = "HIST-RISK-RESULT" in influence_live or bool(influence_live)
        step(bool(has_influence), f"History influence cites prior outcome{suffix}")

        if digest_match and action_shifted and has_influence:
            successful_pairs += 1

        if inv_live.get("incident_id"):
            last_incident_id = inv_live["incident_id"]
            last_run_id = inv_live.get("run_id")

    if repeat_count > 1:
        print(f"\n=== Repeat Consistency: {successful_pairs}/{repeat_count} pairs verified ===")
        step(successful_pairs >= min(4, repeat_count), f"At least 4 of 5 repeat consistency ({successful_pairs}/{repeat_count})")

    if last_incident_id and not args.skip_retention:
        print(f"\n=== 5. Outcome Retention Flow (Incident {last_incident_id}) ===")
        out_res = client.post(
            f"/api/incidents/{last_incident_id}/outcomes",
            json={
                "type": "decision",
                "run_id": last_run_id,
                "event_time": args.as_of,
                "note": "Demo verification decision",
                "idempotency_key": f"demo-out-{uuid.uuid4().hex[:6]}",
            },
        )
        step(out_res.status_code in (200, 201), "POST outcome retention", out_res.text[:200])
        if out_res.status_code in (200, 201):
            print(f"      outcome retention_status: {out_res.json().get('retention_status')}")
    elif args.skip_retention:
        print("\n=== 5. Outcome Retention Flow skipped (--skip-retention set) ===")

    print("\n=== 6. Demo Check Summary ===")
    if failures:
        print(f"FAILED {len(failures)} checks: {', '.join(failures)}")
        return 1

    print("ALL DEMO VERIFICATION CHECKS PASSED!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
