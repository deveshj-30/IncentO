"""The module entry points P3 and P4 export must accept exactly the calls P2 makes.

Runs against whatever `core.modules.resolve()` binds: real modules once they exist, stubs before.
A mismatch here fails loudly instead of becoming a silent `retention_error` at runtime.
"""

import inspect

import pytest

from app.core import modules

# name -> positional arguments P2 passes (see "Signatures P4 implements" in references/contracts-v1.md)
CALLS = {
    "analyze": ("dataset", "policy_id", "as_of"),
    "explain": ("analysis", "context"),
    "retain_outcome": ("outcome", "scenario"),
    "seed_history": ("incidents", "scenario"),
    "reset_demo_bank": ("scenario",),
}


@pytest.mark.parametrize("name,args", CALLS.items())
def test_entry_point_accepts_the_contract_call(name, args):
    fn = getattr(modules.resolve(), name)
    inspect.signature(fn).bind(*args)  # TypeError on a missing or extra required argument
    required = [
        p
        for p in inspect.signature(fn).parameters.values()
        if p.default is inspect.Parameter.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    assert len(required) == len(args), f"{name} requires {[p.name for p in required]}"


def test_every_contract_entry_point_is_covered():
    assert set(CALLS) == {"analyze", "explain", "retain_outcome", "seed_history", "reset_demo_bank"}
