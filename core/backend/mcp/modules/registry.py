"""Factory registry: the per-feature-module surface the pe-modules server stamps.

The pe-modules server is *factory-generated*: rather than hand-writing one
server per module, it derives the module list from the block catalogue and
builds a uniform per-module surface (describe / configure / run-scoped /
doc-resource) from that. This module is the derivation.

A "module" here is a ``modules/<name>/`` feature (the ``pe.features.<name>``
package). We recover the set data-drively: every distinct ``BlockSpec.feature``
in ``pe.blocks.BLOCK_CATALOGUE`` that has an importable ``pe.features.<feature>``
package is a module; the catalogue's non-package features (``core``,
``batch_analysis``, ``calibration``, ``narrative``, ``investment_trigger``,
``feedback_coupling``) are deliberately excluded — those belong to the config
and run servers, not to a per-module surface. So the module list can never
drift from the catalogue or from what actually ships as a feature package.

For each module we resolve:

* its block specs (every catalogue block tagged with that ``feature``),
* its ``doc/reference.md`` mechanism doc (sibling of the feature package on
  disk, resolved through the package's ``__file__`` so the ``package-dir``
  remap is honoured), and
* its *scoped summary columns* — the compact-result keys that carry that
  module's own outputs (e.g. banking -> the bank path, MSR -> the reserve
  pool), used by ``run_module_scoped`` to report just this feature's effect.

Dependency law: same as any T5 app — imports ``pe.blocks`` and stdlib.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from ...blocks import BLOCK_CATALOGUE
from ...blocks.registry import BlockSpec

# ── Scoped summary columns ───────────────────────────────────────────────
# Compact-result per-year keys (pe.mcp.compact.compact_run_summary) that carry
# each module's *own* outputs. Only modules whose effect surfaces as a
# dedicated summary column appear here; a module absent from this map has no
# feature-specific compact column, and run_module_scoped falls back to the
# shared price/abatement headline with a note. The labels mirror
# pe.mcp.compact's _MSR_COLUMNS/_CCR_COLUMNS and the optional bank keys — the
# single source of truth for what compact_run_summary actually emits.
_SCOPED_COLUMNS: dict[str, tuple[str, ...]] = {
    "banking": ("bank", "borrowed"),
    "msr": ("msr_withheld", "msr_released", "msr_reserve_pool"),
    "ccr": ("ccr_cap_adjustment", "ccr_emissions_deviation", "ccr_cost_deviation"),
}

# The catalogue features that are NOT feature-module packages (the config/run
# servers' domain). The importable-package check in module_registry() is what
# actually excludes them; this is the belt-and-braces invariant guard that
# fails loudly if one ever sneaks in as a module (e.g. someone adds a stray
# pe.features.calibration package) — so a silent misclassification can't ship.
_NON_MODULE_FEATURES: frozenset[str] = frozenset(
    {
        "core",
        "batch_analysis",
        "calibration",
        "narrative",
        "investment_trigger",
        "feedback_coupling",
    }
)


@dataclass(frozen=True)
class ModuleInfo:
    """One feature module's factory surface.

    Args:
        name: The feature/module name (``modules/<name>/``, ``pe.features.<name>``).
        blocks: Every catalogue :class:`~pe.blocks.registry.BlockSpec` tagged
            with this ``feature``, in catalogue order.
        doc_path: Absolute path to the module's ``doc/reference.md``, or
            ``None`` if that module ships no reference doc.
        scoped_columns: Compact-result per-year keys carrying this module's
            own outputs (possibly empty).
    """

    name: str
    blocks: tuple[BlockSpec, ...]
    doc_path: Path | None
    scoped_columns: tuple[str, ...] = field(default_factory=tuple)

    @property
    def block_ids(self) -> tuple[str, ...]:
        """The catalogue ids of this module's blocks, in catalogue order."""
        return tuple(b.id for b in self.blocks)


def _resolve_doc_path(feature: str) -> Path | None:
    """Locate ``modules/<feature>/doc/reference.md`` via the feature package.

    Resolves through ``pe.features.<feature>.__file__`` (``.../modules/
    <feature>/backend/__init__.py``) so the ``package-dir`` remap is honoured
    wherever the package is installed. Returns ``None`` if the package or the
    reference doc is absent.
    """
    try:
        module = importlib.import_module(f"pe.features.{feature}")
    except ModuleNotFoundError:
        return None
    package_file = getattr(module, "__file__", None)
    if package_file is None:
        return None
    # .../modules/<feature>/backend/__init__.py -> .../modules/<feature>/doc/reference.md
    doc = Path(package_file).resolve().parent.parent / "doc" / "reference.md"
    return doc if doc.is_file() else None


@cache
def module_registry() -> dict[str, ModuleInfo]:
    """Build the ``{name: ModuleInfo}`` map for every feature module.

    Derived from ``pe.blocks.BLOCK_CATALOGUE``: a distinct ``feature`` becomes
    a module iff ``pe.features.<feature>`` imports (the non-package meta
    features are thereby excluded — see the module docstring). Cached: the
    catalogue is immutable data, so the map is computed once per process.

    Returns:
        ``{name: ModuleInfo}`` keyed by module name, in catalogue-feature
        first-appearance order.
    """
    blocks_by_feature: dict[str, list[BlockSpec]] = {}
    for block in BLOCK_CATALOGUE:
        blocks_by_feature.setdefault(block.feature, []).append(block)

    registry: dict[str, ModuleInfo] = {}
    for feature, blocks in blocks_by_feature.items():
        try:
            importlib.import_module(f"pe.features.{feature}")
        except ModuleNotFoundError:
            continue  # a non-module catalogue feature (core/analysis/...) — skip
        registry[feature] = ModuleInfo(
            name=feature,
            blocks=tuple(blocks),
            doc_path=_resolve_doc_path(feature),
            scoped_columns=_SCOPED_COLUMNS.get(feature, ()),
        )
    leaked = _NON_MODULE_FEATURES & registry.keys()
    if leaked:
        raise RuntimeError(
            f"Non-module catalogue features leaked into the module registry: {sorted(leaked)}. "
            "A pe.features.* package now shadows a config/run-server feature name."
        )
    return registry


def get_module(name: str) -> ModuleInfo:
    """Look up one module's :class:`ModuleInfo` by name.

    Args:
        name: A feature-module name (see :func:`module_registry`).

    Returns:
        The module's :class:`ModuleInfo`.

    Raises:
        KeyError: ``name`` is not a known module (message lists the known set).
    """
    registry = module_registry()
    try:
        return registry[name]
    except KeyError as exc:
        known = ", ".join(sorted(registry))
        raise KeyError(f"Unknown module '{name}'. Known modules: {known}.") from exc
