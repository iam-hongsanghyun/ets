"""Deprecation-shim sweep + ets->pe mirror completeness (D0-R1).

Invariants, all fast (no solving, imports/AST only):

1. EVERY flat backward-compatibility shim fires its own ``DeprecationWarning``
   exactly once per (re-)import, naming its canonical ``pe`` home.
2. The supported import surface stays WARNING-CLEAN: ``pe`` and its
   subpackages must never traverse a warning shim (checked in a fresh
   interpreter with ``-W error::DeprecationWarning``). NOTE the D0-R1
   inversion: ``import ets`` now INTENTIONALLY warns — ``pe.*`` is the clean
   tier, ``ets.*`` the compat/warning tier.
3. MIRROR COMPLETENESS: every ``src/pe`` module has an ``src/ets`` counterpart;
   every ``src/ets`` module imports only ``pe.*`` + stdlib + ``warnings`` (no
   math or logic hides in a shim); every ``src/ets`` module emits exactly one
   own ``DeprecationWarning``.

A shim's module body executes once per import, so re-firing its warning
requires evicting it from ``sys.modules`` and re-importing; parent packages
stay cached, so each check observes ONLY the target module's warning.
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
_PE_ROOT = _SRC / "pe"
_ETS_ROOT = _SRC / "ets"

# Flat shim module (lives at ets.*) -> a phrase its warning must contain (its
# canonical pe home). Regenerated for the ets->pe rename: the shim's own name
# stays ets.* (that is the deprecated path); only the HOME it names is pe.*.
SHIM_WARNINGS: dict[str, str] = {
    # flat shims
    "ets.simulation": "pe.engine",
    "ets.msr": "pe.features.msr",
    "ets.ccr": "pe.features.ccr",
    "ets.hotelling": "pe.engine",
    "ets.nash": "pe.engine",
    "ets.expectations": "pe.core.expectations",
    "ets.scenarios": "pe.config_io",
    "ets.server": "pe.web.server",
    "ets.webapp": "pe.web.handlers",
    "ets.config": "pe.core.paths",
    "ets.costs": "pe.core.costs",
    # shim packages
    "ets.market": "pe.core.market",
    "ets.market.core": "pe.core.market.model",
    "ets.market.equilibrium": "pe.core.market.clearing",
    "ets.market.results": "pe.core.market.reporting",
    "ets.participant": "pe.core.participant",
    "ets.participant.models": "pe.core.participant.models",
    "ets.participant.compliance": "pe.core.participant.compliance",
    "ets.participant.technology": "pe.core.participant.technology",
    # solvers tier (all pure shims)
    "ets.solvers": "pe.engine",
    "ets.solvers.simulation": "pe.engine",
    "ets.solvers.banking": "pe.engine",
    "ets.solvers.hotelling": "pe.engine",
    "ets.solvers.nash": "pe.engine",
    "ets.solvers.transmission": "pe.engine",
    "ets.solvers.msr": "pe.features.msr",
    "ets.solvers.ccr": "pe.features.ccr",
    "ets.solvers.events": "pe.engine",
    "ets.solvers.expectations": "pe.core.expectations",
}

# The supported (non-shim) import surface that must stay warning-clean —
# includes the Vercel serving chain (api/index.py -> pe.web.server).
CLEAN_IMPORTS = (
    "pe",
    "pe.engine",
    "pe.core",
    "pe.config_io",
    "pe.blocks",
    "pe.web.server",
    "pe.coupling",
    "pe.analysis.batch",
    "pe.cli",
    "pe.mcp",
)


@pytest.mark.parametrize("module_name", sorted(SHIM_WARNINGS))
def test_shim_fires_its_deprecation_warning_exactly_once(module_name: str) -> None:
    """Re-importing a flat shim fires exactly one warning with the right text."""
    sys.modules.pop(module_name, None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.import_module(module_name)

    own = [
        w
        for w in caught
        if issubclass(w.category, DeprecationWarning)
        and str(w.message).startswith(f"{module_name} is deprecated")
    ]
    assert len(own) == 1, (
        f"{module_name}: expected exactly one of its own DeprecationWarnings, "
        f"got {len(own)}: {[str(w.message) for w in caught]}"
    )
    message = str(own[0].message)
    assert SHIM_WARNINGS[module_name] in message, (
        f"{module_name}: warning must name the canonical home "
        f"{SHIM_WARNINGS[module_name]!r}; got: {message}"
    )
    assert "milestone" in message.lower(), (
        f"{module_name}: warning must state the removal milestone; got: {message}"
    )


def test_supported_import_surface_is_warning_clean() -> None:
    """The canonical pe import chains never traverse a warning shim.

    Runs in a fresh interpreter (this process has cached, already-warned
    modules) with DeprecationWarning escalated to an error — the Vercel path
    (api/index.py imports pe.web.server) is part of the chain.
    """
    code = "; ".join(f"import {m}" for m in CLEAN_IMPORTS)
    result = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "canonical import surface raised under -W error::DeprecationWarning:\n"
        f"{result.stderr}"
    )


# --------------------------------------------------------------------------
# Mirror completeness (D0-R1): the src/ets compat package mirrors every pe
# module and hides no logic.
# --------------------------------------------------------------------------

_STDLIB = frozenset(sys.stdlib_module_names)


def _ets_modules() -> list[Path]:
    return sorted(_ETS_ROOT.rglob("*.py"))


def _import_targets(node: ast.AST) -> list[str]:
    """Absolute dotted targets of one Import/ImportFrom node (level 0 only)."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level != 0:  # every ets shim imports pe.* ABSOLUTELY
            return [f".<relative level {node.level}>"]
        return [node.module] if node.module else []
    return []


def _is_deprecation_warn(node: ast.AST) -> bool:
    """True if ``node`` is a ``warnings.warn(..., DeprecationWarning, ...)`` call."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr == "warn"
            and isinstance(func.value, ast.Name) and func.value.id == "warnings"):
        return False
    args_and_kwargs = list(node.args) + [kw.value for kw in node.keywords]
    return any(isinstance(a, ast.Name) and a.id == "DeprecationWarning" for a in args_and_kwargs)


def test_every_pe_module_has_an_ets_mirror() -> None:
    """Every ``src/pe`` module has a same-relpath counterpart under ``src/ets``."""
    missing = [
        str(p.relative_to(_PE_ROOT))
        for p in sorted(_PE_ROOT.rglob("*.py"))
        if not (_ETS_ROOT / p.relative_to(_PE_ROOT)).exists()
    ]
    assert not missing, f"pe modules without an ets mirror: {missing}"


def test_ets_modules_import_only_pe_stdlib_and_warnings() -> None:
    """No ``src/ets`` module imports anything but ``pe.*`` and stdlib (incl. warnings).

    A shim that imported a third-party package or reached sideways would be
    hiding real work — the whole point of the compat package is that it is a
    pure re-export layer over ``pe``.
    """
    offenders: list[tuple[str, str]] = []
    for path in _ets_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for target in _import_targets(node):
                top = target.split(".")[0]
                if target == "pe" or target.startswith("pe.") or top in _STDLIB:
                    continue
                offenders.append((str(path.relative_to(_ETS_ROOT)), target))
    assert not offenders, f"ets compat modules import non-pe/non-stdlib names: {offenders}"


def test_each_ets_module_emits_exactly_one_deprecation_warning() -> None:
    """Every ``src/ets`` module fires exactly one own ``DeprecationWarning``."""
    bad: list[tuple[str, int]] = []
    for path in _ets_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        count = sum(1 for node in ast.walk(tree) if _is_deprecation_warn(node))
        if count != 1:
            bad.append((str(path.relative_to(_ETS_ROOT)), count))
    assert not bad, f"ets modules not emitting exactly one DeprecationWarning: {bad}"
