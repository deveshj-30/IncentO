# Demo & Recording Checklist (P4)

Use this checklist before recording the submission video and before the live judging session.

## Pre-Flight Check

- [ ] Backend running locally:
  ```bash
  cd backend
  .venv/bin/python -m uvicorn app.main:create_app --factory --reload
  ```
- [ ] Frontend running locally:
  ```bash
  cd frontend
  npm run dev
  ```
- [ ] `scripts/check.sh` passes 100% cleanly (ruff, pytest, contract drift).
- [ ] Use a fresh private bank for each rehearsal and recording (Cloud does not reliably empty a deleted bank):
  start the backend with `HINDSIGHT_BANK_SUFFIX=<new word>` and `DEMO_RESET_ENABLED=true`, then call
  `POST /api/demo/reset` once with `{"scenario": "risk", "confirm": true}` to load the history into the new bank.
  Never run outcome-writing tests against the shared `incento-demo-risk` bank.
- [ ] Check Hindsight Cloud credits first: with a zero balance every call returns HTTP 402 and live recall is empty.
- [ ] Repeat check (reads only): `backend/.venv/bin/python scripts/demo_check.py --repeat 5 --skip-retention`.
- [ ] After saving an outcome, wait about 15 seconds before investigating again.
- [ ] Verify `HINDSIGHT_API_KEY` is set if running against live Hindsight Cloud, or verify fallback behavior.

## Recording Guidelines (Deliverables Checklist)

- [ ] **Demo Video**:
  - Keep under 3 minutes total (ideal: 90 seconds to 2 minutes).
  - High resolution (1080p), clean audio, no background noise.
  - Clearly show the split comparison: **Memory OFF vs. Memory LIVE**.
  - Show the persistence payoff: save an outcome and recall it in the subsequent step.
- [ ] **Content Deliverables (Hackathon Content Guide)**:
  - Technical article published (explaining how Hindsight memory powers IncentO).
  - Social media post (X / LinkedIn) with live demo clips.
  - Clean GitHub repo with no secrets in code or commits.

## Notes moved from the old README

- **Private bank:** for a recording or the live judging session set `HINDSIGHT_BANK_SUFFIX=<word>` (for example `final1`), start the backend, and call `POST /api/demo/reset` once with `{"scenario": "risk", "confirm": true}` (needs `DEMO_RESET_ENABLED=true`). History is loaded into the new, empty bank `incento-demo-risk-<word>`. Hindsight Cloud does not reliably empty a deleted bank, so a new suffix is more dependable than resetting the shared bank.
- **Offline run:** `HINDSIGHT_SIMULATE=1` with no key uses a local file and is always shown as `fixture`.
- **Wait after saving an outcome:** about 15 seconds before investigating again, because Cloud indexes a new record a little later.
- **Reflect is off by default** (its wording breaks the no-causation rule and each call spends credits). Set `HINDSIGHT_REFLECT=1` to try it. The explanation is then the labeled template and the memory status stays `live`.
- **Credits:** when the Hindsight balance runs out every call returns HTTP 402, live recall is empty, and the app reports memory as `unavailable` instead of faking it.
- **Real key:** `HINDSIGHT_API_KEY` goes only in `backend/.env`. Real calls write to the team account's bank `incento-demo-<scenario>`, so running `scripts/smoke_test.py` against Cloud adds a test outcome to the memory the demo uses. Agree a time with P4 first.
- **Checks:** `scripts/g4_check.py` (simulation memory, no Cloud writes; `--cloud` uses the throwaway bank `incento-demo-p2dev`), `scripts/demo_check.py --repeat 5 --skip-retention` (memory off versus live gives different actions with identical numbers; read-only on Cloud), `scripts/smoke_test.py --base-url http://localhost:8000 --scenario <name>` (full API flow against a running server). Contracts are generated from `backend/app/core/schemas.py`: after changing a model run `backend/.venv/bin/python scripts/export_contracts.py` and commit the regenerated `contracts/` files.
