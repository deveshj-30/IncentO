#!/usr/bin/env python3
"""Write contracts/openapi.json and contracts/schemas/*.json from the Pydantic models.

Usage: python scripts/export_contracts.py [--check]
--check fails (exit 1) if committed files differ from regenerated output.
Run with the backend virtualenv: backend/.venv/bin/python scripts/export_contracts.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import TypeAdapter  # noqa: E402

from app.core import schemas  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

app = create_app(Settings(database_path=":memory:"))

SCHEMA_FILES = {
    "analysis.schema.json": schemas.AnalysisResult,
    "investigation.schema.json": schemas.Investigation,
    "investigation-request.schema.json": schemas.InvestigationRequest,
    "error.schema.json": schemas.ErrorResponse,
    "dataset.schema.json": schemas.Dataset,
    "outcome.schema.json": schemas.Outcome,
    "outcome-request.schema.json": schemas.OutcomeRequest,
}


def render(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def outputs() -> dict[Path, str]:
    out = {ROOT / "contracts" / "openapi.json": render(app.openapi())}
    for name, model in SCHEMA_FILES.items():
        out[ROOT / "contracts" / "schemas" / name] = render(TypeAdapter(model).json_schema())
    return out


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale = []
    for path, text in outputs().items():
        if check:
            if not path.exists() or path.read_text() != text:
                stale.append(path.relative_to(ROOT))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    if stale:
        print("Stale contract files (run scripts/export_contracts.py):", *map(str, stale), sep="\n  ")
        return 1
    print("Contracts up to date" if check else "Contracts written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
