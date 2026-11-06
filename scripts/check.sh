#!/usr/bin/env bash
# Run every available check. Usage: scripts/check.sh   (from anywhere)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"
[ -x "$PY" ] || { echo "Missing backend/.venv; see README.md setup" >&2; exit 2; }

echo "== backend: ruff =="
(cd "$ROOT/backend" && "$PY" -m ruff check .)
echo "== backend: pytest =="
(cd "$ROOT/backend" && "$PY" -m pytest -q)
echo "== contracts: drift check =="
"$PY" "$ROOT/scripts/export_contracts.py" --check

if [ -f "$ROOT/frontend/package.json" ]; then
  echo "== frontend =="
  (cd "$ROOT/frontend" && npm run lint && npm test --if-present && npm run build)
  echo "== frontend: generated types drift =="
  (cd "$ROOT/frontend" && npm run gen:types && git diff --exit-code -- src/types/contracts.ts)
else
  echo "== frontend: skipped (frontend/package.json not present yet) =="
fi
echo "All checks passed"
