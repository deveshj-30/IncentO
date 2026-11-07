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
- [ ] Reset the demo memory bank before each rehearsal:
  ```bash
  backend/.venv/bin/python scripts/demo_check.py --scenario incentive-risk
  ```
- [ ] Verify `HINDSIGHT_API_KEY` is set if running against live Hindsight Cloud, or verify fallback behavior.

## Recording Guidelines (Deliverables Checklist)

- [ ] **Demo Video**:
  - Keep under 3 minutes total (ideal: 90 seconds to 2 minutes).
  - High resolution (1080p), clean audio, no background noise.
  - Clearly show the split comparison: **Memory OFF vs. Memory LIVE**.
  - Show the persistence payoff: save an outcome and recall it in the subsequent step.
- [ ] **Content Deliverables (Hackathon Content Guide)**:
  - Technical article published (explaining how Hindsight memory powers IncentiveTrap).
  - Social media post (X / LinkedIn) with live demo clips.
  - Clean GitHub repo with no secrets in code or commits.
