"""Resolve the analysis and memory entry points; fall back to labeled stubs.

Real modules are used automatically once ``app.analysis.service`` and ``app.memory.service`` exist
and export the agreed names. ``stubbed`` reports which pieces are still stubs.
"""

import importlib
from dataclasses import dataclass
from typing import Any

from app.core import stubs

_NAMES = {
    "app.analysis.service": ["analyze"],
    "app.memory.service": ["explain", "retain_outcome", "seed_history", "reset_demo_bank"],
}


@dataclass
class Modules:
    analyze: Any
    explain: Any
    retain_outcome: Any
    seed_history: Any
    reset_demo_bank: Any
    stubbed: list[str]


def resolve() -> Modules:
    chosen: dict[str, Any] = {}
    stubbed: list[str] = []
    for module_name, names in _NAMES.items():
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name != module_name and not module_name.startswith(exc.name or "\0"):
                raise
            module = None
        for name in names:
            fn = getattr(module, name, None) if module else None
            if fn is None:
                fn = getattr(stubs, name)
                stubbed.append(name)
            chosen[name] = fn
    return Modules(stubbed=stubbed, **chosen)
