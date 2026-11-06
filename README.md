# IncentiveTrap

Hackathon MVP that investigates whether an acquisition-based sales commission may be producing poor-fit SaaS deals. Synthetic data, replay demo, no causal claims. Read `AGENTS.md`, `agent_help.md`, and `implementation_plan.md` first; `progress.md` holds current status.

## Backend quick start

```bash
cd backend
uv venv --python 3.14 .venv            # Python 3.12+ works
uv pip install --python .venv/bin/python -r requirements.txt
cp ../.env.example .env                # optional; add secrets locally only
.venv/bin/python -m uvicorn app.main:create_app --factory --reload   # http://localhost:8000/api/health
```

## Checks and contracts

- `scripts/check.sh` runs lint, tests, and the contract drift check (and frontend checks once `frontend/` exists).
- Contracts are generated from `backend/app/core/schemas.py`. After changing a model run `backend/.venv/bin/python scripts/export_contracts.py` and commit the regenerated `contracts/` files. Never hand-edit generated files.
- `contracts/v1.md` explains semantics; `contracts/examples/*.json` must parse into the models (tested).

## Folders

`backend/` API and core (P2), `frontend/` (P1), `data/` (P3), `backend/app/analysis/` (P3), `backend/app/memory/` and `docs/demo/` (P4), `scripts/` (P2; `demo_check.py` is P4's). Folder READMEs are written by their owners.
