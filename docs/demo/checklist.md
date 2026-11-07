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
