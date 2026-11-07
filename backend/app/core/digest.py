"""analysis_digest: SHA-256 over the canonical JSON of an AnalysisResult.

Two runs of the same inputs must produce the same digest regardless of memory mode.
Display-only text is left out, so rewording a ticket excerpt or an alternative's label
cannot change the digest while every number, ID and timestamp still can.
"""

import hashlib
import json

from app.core.schemas import AnalysisResult

# Fields whose only job is to be shown to a person (see the Evidence docstring in schemas.py).
_DISPLAY_ONLY = {"evidence": {"excerpt"}, "alternatives": {"label"}}


def canonical_analysis(analysis: AnalysisResult) -> dict:
    data = analysis.model_dump(mode="json")
    for section, fields in _DISPLAY_ONLY.items():
        data[section] = [{k: v for k, v in item.items() if k not in fields} for item in data[section]]
    return data


def analysis_digest(analysis: AnalysisResult) -> str:
    canonical = json.dumps(canonical_analysis(analysis), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
