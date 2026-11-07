# IncentO

Hackathon MVP that investigates whether an acquisition-based sales commission may be producing poor-fit SaaS deals. Synthetic data, replay demo, no causal claims. Read `AGENTS.md`, `agent_help.md`, and `implementation_plan.md` first; `progress.md` holds current status.

## Backend quick start

```bash
cd backend
uv venv --python 3.14 .venv            # Python 3.12+ works
uv pip install --python .venv/bin/python -r requirements.txt
cp ../.env.example .env                # optional; secrets stay in this git-ignored file
.venv/bin/python -m uvicorn app.main:create_app --factory --reload   # http://localhost:8000/api/health
```

## Frontend quick start

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173, proxies /api to the backend on port 8000
```

Start the backend first. The header always shows `Synthetic data`, the memory status (`live`, `fixture` or `unavailable`) and the explanation source (`template` or `reflect`).

## Running the demo

1. Backend with the team key in `backend/.env` (`memory: live`), or `HINDSIGHT_SIMULATE=1` with no key for an offline run that is shown as `fixture`.
2. For a recording or the live judging session, use a fresh private bank so nobody else's test runs change the history: set `HINDSIGHT_BANK_SUFFIX=<word>` (for example `final1`), start the backend, and call `POST /api/demo/reset` once with `{"scenario": "risk", "confirm": true}` (needs `DEMO_RESET_ENABLED=true`) so the history is loaded into the new, empty bank `incento-demo-risk-<word>`. Hindsight Cloud does not reliably empty a deleted bank, so a new suffix is more dependable than resetting the shared bank.
3. Follow `docs/demo/script.md`. Wait about 15 seconds after saving an outcome before investigating again, because Cloud indexes a new record a little later.
4. Reflect is off by default (its wording breaks the no-causation rule and each call spends credits); set `HINDSIGHT_REFLECT=1` to try it. The explanation is then the labeled template and the memory status stays `live`.
5. Hindsight Cloud needs credits. When the balance runs out, every call returns HTTP 402 and live recall returns nothing, and the app reports memory as `unavailable` instead of faking it.

## Checks and contracts

- `scripts/check.sh` runs lint, tests, and the contract drift check (and frontend checks once `frontend/` exists).
- `scripts/g4_check.py` starts the API twice on a throwaway database and checks outcome retention, idempotent replay, retention retry, `as_of_before_memory`, restart persistence and recall of the saved outcomes. It uses simulation memory and writes nothing to Cloud; `--cloud` repeats it against Cloud on the throwaway bank `incento-demo-p2dev` (never `incento-demo-risk`).
- `scripts/demo_check.py --repeat 5 --skip-retention` checks that memory off versus live gives different actions with identical numbers; it only reads from Cloud.
- `scripts/smoke_test.py --base-url http://localhost:8000 --scenario <name>` runs the full API flow against a running server (needs a loaded fixture in `data/scenarios/`).
- Contracts are generated from `backend/app/core/schemas.py`. After changing a model run `backend/.venv/bin/python scripts/export_contracts.py` and commit the regenerated `contracts/` files. Never hand-edit generated files.
- `contracts/v1.md` explains semantics; `contracts/examples/*.json` must parse into the models (tested).

## Folders

`backend/` API and core (P2), `frontend/` (P1), `data/` (P3), `backend/app/analysis/` (P3), `backend/app/memory/` and `docs/demo/` (P4), `scripts/` (P2; `demo_check.py` is P4's). Folder READMEs are written by their owners.

## Using the real Hindsight key

Put `HINDSIGHT_API_KEY` in `backend/.env` (see `.env.example`). Real calls write to the team account's demo bank `incento-demo-<scenario>`, so running `scripts/smoke_test.py` against Cloud adds a test outcome to the memory the demo uses. Agree a time with P4 first, and afterwards reset the scenario (`DEMO_RESET_ENABLED=true`, then `POST /api/demo/reset` with `{"scenario": "risk", "confirm": true}`), which deletes and reseeds that bank. Without a key, memory reports `memory_not_configured`; `HINDSIGHT_SIMULATE=1` uses a local file and is always labeled `fixture`.
