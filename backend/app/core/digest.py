"""analysis_digest: SHA-256 over the canonical JSON of an AnalysisResult.

Two runs of the same inputs must produce the same digest regardless of memory mode.
"""

import hashlib
import json

from app.core.schemas import AnalysisResult


def analysis_digest(analysis: AnalysisResult) -> str:
    canonical = json.dumps(analysis.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
