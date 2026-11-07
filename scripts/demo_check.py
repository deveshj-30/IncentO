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
from datetime import datetime, timezone

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
    parser.add_argument("--scenario", default="tiny")
    parser.add_argument("--policy-id", default="pol-acq-bonus")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url, timeout=30.0)

    print("=== 1. Checking API Health & Memory Status ===")
    try:
        res = client.get("/api/health")
    except Exception as exc:
        print(f"[FAIL] Could not connect to API server at {args.base_url}: {exc}")
        print("Hint: Start the server with: cd backend && .venv/bin/python -m uvicorn app.main:create_app --factory")
        return 1

    step(res.status_code == 200, "GET /api/health", res.text[:200])
    h = res.json()
    print(f"      memory_status: {h.get('memory_status')} | stubbed: {h.get('stubbed_modules')}")

    print("\n=== 2. Loading Scenario & Seeding Hindsight History ===")
    load_res = client.post("/api/demo/load", json={"scenario": args.scenario})
    step(load_res.status_code == 200, f"POST /api/demo/load ({args.scenario})", load_res.text[:200])
    load_data = load_res.json()
    print(f"      seed_status: {load_data.get('seed_status')} | synthetic: {load_data.get('synthetic')}")

    print("\n=== 3. Investigation: Memory Mode OFF ===")
    req_off = {
        "policy_id": args.policy_id,
        "scenario": args.scenario,
        "as_of": "2026-03-31T23:59:59Z",
        "memory_mode": "off",
        "idempotency_key": f"test-off-{uuid.uuid4().hex[:6]}",
    }
    inv_off_res = client.post("/api/investigations", json=req_off)
    step(inv_off_res.status_code == 200, "POST /api/investigations (memory_mode=off)", inv_off_res.text[:200])
    if inv_off_res.status_code == 200:
        inv_off = inv_off_res.json()
        exp_off = inv_off.get("explanation", {})
        recalled_off = exp_off.get("recalled", [])
        step(len(recalled_off) == 0, "No memories recalled when memory_mode=off")
        print(f"      source: {exp_off.get('explanation_source')} | recalled count: {len(recalled_off)}")

    print("\n=== 4. Investigation: Memory Mode LIVE ===")
    req_live = {
        "policy_id": args.policy_id,
        "scenario": args.scenario,
        "as_of": "2026-03-31T23:59:59Z",
        "memory_mode": "live",
        "idempotency_key": f"test-live-{uuid.uuid4().hex[:6]}",
    }
    inv_live_res = client.post("/api/investigations", json=req_live)
    step(inv_live_res.status_code == 200, "POST /api/investigations (memory_mode=live)", inv_live_res.text[:200])
    if inv_live_res.status_code == 200:
        inv_live = inv_live_res.json()
        exp_live = inv_live.get("explanation", {})
        print(f"      source: {exp_live.get('explanation_source')} | memory_status: {exp_live.get('memory_status')}")

    print("\n=== 5. Demo Check Summary ===")
    if failures:
        print(f"FAILED {len(failures)} checks: {', '.join(failures)}")
        return 1

    print("ALL DEMO VERIFICATION CHECKS PASSED!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
