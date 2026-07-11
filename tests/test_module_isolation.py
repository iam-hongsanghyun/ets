"""AST-based import-contract ratchet for the feature-module migration.

Enforces the tier contract of `docs/feature-modules-plan.md` §1 by parsing
every module under `src/pe` with `ast` (no `ets` code is ever imported —
this must stay fast and side-effect free) and asserting that no forbidden
import edge exists between tiers.

Algorithm:
    Not a numerical algorithm; this is a static-analysis ratchet. The
    "algorithm" is graph construction + predicate checks:

        1. For every `.py` file under `src/pe`, `ast.parse` it and
           `ast.walk` the *entire* tree (module scope AND nested
           function/method bodies, so lazy imports count) collecting every
           `Import`/`ImportFrom` node.
        2. Resolve each import to an absolute `pe.*` dotted module name.
           Relative imports (`level > 0`) are resolved with
           `importlib.util.resolve_name` against the *importing* file's own
           package (its containing directory, or itself for `__init__.py`).
        3. Classify every module name into a tier by path prefix (T0..T5,
           SHIM, or LEGACY — see `classify`).
        4. Build the edge set `EDGES = {(src_module, dst_module), ...}`
           (deduplicated, `pe.*` targets only — stdlib/third-party imports
           are irrelevant to tier isolation and are dropped).
        5. Each contract clause (a)-(h) of the plan is one `test_*`
           function: filter `EDGES` for the clause's forbidden shape, drop
           anything already listed in `PENDING_VIOLATIONS` (the seeded
           allowlist of edges a later work order removes), and assert the
           remainder is empty.
        6. `PENDING_VIOLATIONS` is itself checked for staleness: an entry
           whose edge no longer exists in `EDGES` fails the suite, so the
           allowlist can only shrink toward empty (O14).

    Tier precedence: SHIM (exact module-name match) is checked before the
    path-prefix tiers, so a bare flat-shim name (e.g. `pe.market`) is never
    mistaken for its same-named sub-package (`pe.market.core` is LEGACY —
    "everything under ets not yet in a target tier or shim").

    Self-tier imports are always implicitly permitted (e.g. `pe.config_io`
    importing `pe.config_io.builder`) — none of the plan's clauses forbid a
    tier from depending on its own submodules, and clause (g) says so
    explicitly for `blocks`/`coupling` ("+ itself").

    Underscore-boundary clause (h): a leading-underscore `ImportFrom` name
    crossing a tier boundary is forbidden *unless either endpoint is SHIM or
    LEGACY* — a flat compat shim's entire purpose is to re-export whatever
    the pre-migration flat module exposed (including private helpers), and
    LEGACY code is explicitly grandfathered ("exempt from tier rules but
    still edge-collected", plan §3). (Historical note: the plan's original
    example — `solvers/hotelling.py`/`solvers/nash.py` importing
    `solvers/simulation.py:_simulate_path_details` — retired with the
    ledger move, v1 O7 / v2 O11: the ledger names are public in
    `core/ledger.py` and only SHIM modules re-export the underscore
    spellings.)

    Door-granular two-door contract (PLAN v2 §"Two-door features", O7):
    `pe.features` now exists, and PLAN v2 supersedes the v1 reading of
    clauses (c) and (e) for exactly one edge shape — `pe.config_io` may
    import `pe.features.<X>.plugin`, and ONLY that module (a feature's
    config-facing door: field specs, build-time transforms, attachable
    reporters/overlays/carriers; imports `pe.core.*` + stdlib only).
    `_is_plugin_door` checks this file-exact, not package-exact: a feature's
    bare package (`pe.features.cbam`, i.e. its `__init__.py`) and its
    runtime modules (`pe.features.<X>.solver`/`rules`/`state`, none exist
    yet) are NOT doors — those stay reachable only from `pe.engine` (T3)
    and same-feature siblings, exactly as clause (c) already required. This
    is the file's edit point for later work orders that add runtime feature
    modules: widen `_is_plugin_door`'s allowed *importers* only if a new
    door type is deliberately introduced, never widen it to match more than
    the literal `plugin` submodule.

References:
    docs/feature-modules-plan.md §1 (tier table), §3 (this test's spec);
    PLAN v2 §"Two-door features"; Arbitration outcomes (O7 binding
    conditions).
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Discovery: map each physical package root to its import-name prefix (mirrors
# [tool.setuptools.package-dir]). The `pe` backend block lives at core/backend/;
# each peeled feature lives at modules/<name>/backend/ and is auto-discovered by
# the glob below, so a new module needs no edit here. `compat/ets` is never
# walked (this ratchet never walked `ets`). Never hardcode an absolute path —
# resolve relative to this test file (tests/ at repo root per CLAUDE.md).
# --------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent

# physical root -> import-name prefix (mirrors package-dir)
_ROOTS: dict[Path, str] = {_REPO_ROOT / "core" / "backend": "pe"}
for _b in sorted((_REPO_ROOT / "modules").glob("*/backend")):
    _ROOTS[_b] = f"pe.features.{_b.parent.name}"

_STDLIB_MODULES = frozenset(sys.stdlib_module_names)

# SHIM tier (plan §1 "Supplementary" + §3). RESERVED, intentionally EMPTY after
# the D0-R1 package rename: src/pe is shim-free — every backward-compatibility
# shim now lives in the separate `ets/` compat package, which this suite does
# NOT walk (`_PKG_ROOT` points at src/pe). The SHIM classification/exemption
# machinery below is kept intact so a future lead-modeller-approved order can
# re-register a shim module name here without re-plumbing the walker.
SHIM_MODULES: frozenset[str] = frozenset()

# T4 sub-packages that must never import each other's siblings (clause g).
_T4_GROUPS: frozenset[str] = frozenset({"analysis", "coupling", "blocks"})

# Edge (importing_module, imported_module) -> work order that removes it.
# Seeded by RUNNING the walker below against the current tree (see module
# docstring); an edge that no longer exists is a stale allowlist entry and
# fails `test_pending_violations_allowlist_has_no_stale_entries`, so this
# dict can only shrink. Target state (O14): empty.
# FLIPPED (v1 O14 / v2 O19): the allowlist reached its target state — empty —
# and STAYS empty. The `_assert_no_violations` machinery is kept so a future
# lead-modeller-APPROVED work order can stage a temporary edge (mapping it to
# the order that removes it), but `test_ratchet_is_flipped_allowlist_empty`
# fails on ANY entry: never add one just to make a red suite green.
PENDING_VIOLATIONS: dict[tuple[str, str], str] = {}


# --------------------------------------------------------------------------
# Tier classification
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ModuleInfo:
    """Tier classification of a single `pe.*` dotted module name.

    Attributes:
        name: Fully-qualified module name, e.g. `"pe.config_io.builder"`.
        tier: One of `"T0"`..`"T5"`, `"SHIM"`, or `"LEGACY"`.
        feature: Third path component (feature name) when `tier == "T2"`,
            else `None`.
        t4_group: Second path component (`"analysis"`/`"coupling"`/
            `"blocks"`) when `tier == "T4"`, else `None`.
    """

    name: str
    tier: str
    feature: str | None = None
    t4_group: str | None = None


def classify(module: str) -> ModuleInfo:
    """Classify an `pe.*` module name into its architectural tier.

    Path-prefix classification only — does not require the target
    directory (`core/`, `features/`, `engine/`) to exist yet, so the
    ratchet stays correct as later work orders create them.

    Args:
        module: Fully-qualified dotted module name, e.g. `"pe.solvers.msr"`.

    Returns:
        The module's `ModuleInfo`.
    """
    if module in SHIM_MODULES:
        return ModuleInfo(module, "SHIM")

    parts = module.split(".")

    if module == "pe.core" or module.startswith("pe.core."):
        return ModuleInfo(module, "T0")
    if module == "pe.config_io" or module.startswith("pe.config_io."):
        return ModuleInfo(module, "T1")
    if module == "pe.features" or module.startswith("pe.features."):
        feature = parts[2] if len(parts) > 2 else None
        return ModuleInfo(module, "T2", feature=feature)
    if module == "pe.engine" or module.startswith("pe.engine."):
        return ModuleInfo(module, "T3")
    if len(parts) >= 2 and parts[1] in _T4_GROUPS:
        return ModuleInfo(module, "T4", t4_group=parts[1])
    if (
        module == "pe.cli"
        or module == "pe.web"
        or module.startswith("pe.web.")
        or module == "pe.mcp"
        or module.startswith("pe.mcp.")
    ):
        return ModuleInfo(module, "T5")

    # Everything else currently under ets (pe.solvers.*, pe.market.*,
    # pe.participant.*, and the top-level `ets` package itself) — exempt
    # from tier rules but still edge-collected (plan §3).
    return ModuleInfo(module, "LEGACY")


def _is_plugin_door(module: str) -> bool:
    """Return True if `module` is exactly a feature's `plugin` config door.

    File-exact, not package-exact (PLAN v2 §"Two-door features"): matches
    `pe.features.<X>.plugin` only — a feature's bare package
    (`pe.features.<X>`, i.e. its `__init__.py`) and its runtime modules
    (`pe.features.<X>.solver`/`rules`/`state`, ...) do NOT match. This is
    the door-granularity check clauses (c) and (e) use to grant
    `pe.config_io` read access to exactly the config-facing door and
    nothing else in a feature package.

    Args:
        module: Fully-qualified dotted module name.

    Returns:
        True iff `module` is `pe.features.<feature>.plugin`.
    """
    parts = module.split(".")
    return len(parts) == 4 and parts[0] == "pe" and parts[1] == "features" and parts[3] == "plugin"


# --------------------------------------------------------------------------
# AST walk: collect every Import/ImportFrom edge, including lazy ones.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RawImport:
    """A single resolved import edge, with the imported name if known.

    Attributes:
        src: Importing module's fully-qualified name.
        dst: Imported module's fully-qualified name (resolved absolute).
        imported_name: The `ImportFrom` alias name (e.g. `"_helper"`), or
            `None` for a plain `import dst` statement.
        lineno: Source line of the import statement, for diagnostics.
    """

    src: str
    dst: str
    imported_name: str | None
    lineno: int


def _iter_py_files() -> Iterator[Path]:
    """Yield every `.py` file under each walked package root, ordered."""
    for root in _ROOTS:
        yield from sorted(root.rglob("*.py"))


def _module_name_for(path: Path) -> str:
    """Return the dotted module name a source file defines.

    Args:
        path: Absolute path to a `.py` file under one of `_ROOTS`.

    Returns:
        Dotted module name, e.g. `core/backend/config_io/builder.py` ->
        `"pe.config_io.builder"`; `__init__.py` files map to their
        containing package, e.g. `core/backend/config_io/__init__.py` ->
        `"pe.config_io"`.
    """
    for root, prefix in _ROOTS.items():
        if root in path.parents or root == path.parent:
            rel = list(path.relative_to(root).with_suffix("").parts)
            if rel and rel[-1] == "__init__":
                rel = rel[:-1]
            return ".".join([prefix, *rel]) if rel else prefix
    raise AssertionError(path)


def _package_name_for(path: Path) -> str:
    """Return the dotted package name used to resolve relative imports.

    Mirrors Python's `__package__` semantics: a package's `__init__.py`
    resolves relative imports against itself; a plain module resolves
    against its containing directory.

    Args:
        path: Absolute path to a `.py` file under one of `_ROOTS`.

    Returns:
        Dotted package name.
    """
    for root, prefix in _ROOTS.items():
        if root in path.parents or root == path.parent:
            rel = list(path.relative_to(root).with_suffix("").parts)
            full = [*prefix.split("."), *rel]
            return ".".join(full[:-1])
    raise AssertionError(path)


def _resolve_import_from(node: ast.ImportFrom, package: str) -> str:
    """Resolve an `ImportFrom` node's `module` to an absolute dotted name.

    Args:
        node: The `ast.ImportFrom` node.
        package: Dotted package name of the importing file (see
            `_package_name_for`), used as the anchor for relative imports.

    Returns:
        Absolute dotted module name, e.g. `"pe.config_io.templates"`.
    """
    if node.level:
        return importlib.util.resolve_name("." * node.level + (node.module or ""), package)
    assert node.module is not None  # absolute `from x import y` always has a module
    return node.module


def _is_pe_module(name: str) -> bool:
    """Return True if `name` is `ets` or a dotted sub-module of `ets`."""
    return name == "pe" or name.startswith("pe.")


def _collect_raw_imports() -> list[RawImport]:
    """Walk every file under each `_ROOTS` package root and collect all edges.

    Walks the *entire* AST (`ast.walk`), not just module-level statements,
    so function-level (lazy) imports are counted. Only edges targeting
    `pe.*` are kept — stdlib/third-party imports don't participate in
    tier isolation.

    Returns:
        All `pe.*`-targeting import edges found in the current tree.
    """
    raw: list[RawImport] = []
    for path in _iter_py_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        module = _module_name_for(path)
        package = _package_name_for(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_pe_module(alias.name):
                        raw.append(RawImport(module, alias.name, None, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                dst = _resolve_import_from(node, package)
                if not _is_pe_module(dst):
                    continue
                for alias in node.names:
                    raw.append(RawImport(module, dst, alias.name, node.lineno))
    return raw


_RAW_IMPORTS: list[RawImport] = _collect_raw_imports()

# Deduplicated (src_module, dst_module) edges, used by the tier-shape
# assertions (a)-(g); (h) uses `_RAW_IMPORTS` directly for the per-name check.
EDGES: frozenset[tuple[str, str]] = frozenset((r.src, r.dst) for r in _RAW_IMPORTS)


# --------------------------------------------------------------------------
# Shared assertion helper
# --------------------------------------------------------------------------


def _assert_no_violations(edges: Iterable[tuple[str, str]], *, rule: str) -> None:
    """Fail with a readable report if any edge is not in `PENDING_VIOLATIONS`.

    Args:
        edges: Candidate offending `(src_module, dst_module)` edges.
        rule: Short label identifying which contract clause is being
            checked, included in the failure message.
    """
    offending = sorted(set(edges) - PENDING_VIOLATIONS.keys())
    assert not offending, (
        f"{rule}: forbidden import edge(s) not covered by PENDING_VIOLATIONS "
        f"(add a seeded entry mapping to the work order that removes it, or "
        f"fix the import): {offending}"
    )


# --------------------------------------------------------------------------
# (a)-(h) contract assertions
# --------------------------------------------------------------------------


def test_no_feature_imports_another_feature() -> None:
    """Clause (a): `pe.features.X` never imports `pe.features.Y`, X != Y."""
    bad = [
        (s, d)
        for s, d in EDGES
        if (si := classify(s)).tier == "T2"
        and (di := classify(d)).tier == "T2"
        and si.feature != di.feature
    ]
    _assert_no_violations(bad, rule="(a) no feature-to-feature imports")


def test_features_import_only_core() -> None:
    """Clause (b): features import only `pe.core.*` (never `pe.config_io`)."""
    bad = []
    for s, d in EDGES:
        si, di = classify(s), classify(d)
        if si.tier != "T2":
            continue
        if di.tier == "T0":
            continue
        if di.tier == "T2" and di.feature == si.feature:
            continue  # same feature, different file within it
        bad.append((s, d))
    _assert_no_violations(bad, rule="(b) features import only core")


def test_features_imported_only_from_engine_or_shim() -> None:
    """Clause (c), door-granular under PLAN v2: `pe.features.*` is imported
    only from engine or a shim — EXCEPT a feature's `plugin` door
    (`pe.features.<X>.plugin` exactly), which `pe.config_io` may also
    import (the two-door contract; see `_is_plugin_door` and the module
    docstring). A feature's runtime modules stay reachable only from engine/
    shim/same-feature, unchanged from v1.
    """
    bad = []
    for s, d in EDGES:
        si, di = classify(s), classify(d)
        if di.tier != "T2":
            continue
        if si.tier in {"T3", "SHIM"}:
            continue
        if si.tier == "T1" and _is_plugin_door(d):
            continue  # PLAN v2 two-door contract: config_io -> plugin door
        if si.tier == "T2" and si.feature == di.feature:
            continue  # internal same-feature edge, not an external importer
        bad.append((s, d))
    _assert_no_violations(
        bad, rule="(c) features imported only from engine/shim (+ config_io->plugin door)"
    )


def test_core_imports_only_core() -> None:
    """Clause (d): `pe.core.*` imports only `pe.core.*`."""
    bad = [(s, d) for s, d in EDGES if classify(s).tier == "T0" and classify(d).tier != "T0"]
    _assert_no_violations(bad, rule="(d) core imports only core")


def test_config_io_imports_only_core() -> None:
    """Clause (e), door-granular under PLAN v2 (supersedes the v1 reading):
    `pe.config_io.*` imports only `pe.core.*` (within ets) OR a feature's
    `plugin` door EXACTLY (`pe.features.<X>.plugin`; see `_is_plugin_door`)
    — never a feature's bare package or its runtime modules
    (`pe.features.<X>.solver`/`rules`/`state`). PLAN v2 "Two-door features"
    is what widens clause (e); door granularity is what keeps the widening
    contained to one reviewed module per feature.
    """
    bad = []
    for s, d in EDGES:
        si, di = classify(s), classify(d)
        if si.tier != "T1":
            continue
        if di.tier in {"T0", "T1"}:
            continue
        if di.tier == "T2" and _is_plugin_door(d):
            continue
        bad.append((s, d))
    _assert_no_violations(bad, rule="(e) config_io imports only core + feature plugin doors")


def test_engine_excludes_workflows_and_apps() -> None:
    """Clause (f): `pe.engine.*` imports nothing from T4 (workflows) or T5 (apps)."""
    bad = [
        (s, d) for s, d in EDGES if classify(s).tier == "T3" and classify(d).tier in {"T4", "T5"}
    ]
    _assert_no_violations(bad, rule="(f) engine excludes workflows/apps")


def test_analysis_modules_do_not_import_each_other() -> None:
    """Clause (g): within `pe.analysis`, sibling modules never import each other."""
    bad = [
        (s, d)
        for s, d in EDGES
        if (si := classify(s)).tier == "T4"
        and si.t4_group == "analysis"
        and (di := classify(d)).tier == "T4"
        and di.t4_group == "analysis"
        and s != d
    ]
    _assert_no_violations(bad, rule="(g) analysis siblings mutually isolated")


def test_blocks_imports_only_config_io_or_itself() -> None:
    """Clause (g): `pe.blocks` imports only `pe.config_io` (T1) or itself."""
    bad = []
    for s, d in EDGES:
        si = classify(s)
        if si.tier != "T4" or si.t4_group != "blocks":
            continue
        di = classify(d)
        if di.tier == "T1":
            continue
        if di.tier == "T4" and di.t4_group == "blocks":
            continue
        bad.append((s, d))
    _assert_no_violations(bad, rule="(g) blocks imports config_io + itself only")


def test_coupling_imports_only_core_config_io_engine_or_itself() -> None:
    """Clause (g): `pe.coupling` imports only core/config_io/engine or itself."""
    allowed_tiers = {"T0", "T1", "T3"}
    bad = []
    for s, d in EDGES:
        si = classify(s)
        if si.tier != "T4" or si.t4_group != "coupling":
            continue
        di = classify(d)
        if di.tier in allowed_tiers:
            continue
        if di.tier == "T4" and di.t4_group == "coupling":
            continue
        bad.append((s, d))
    _assert_no_violations(bad, rule="(g) coupling imports core/config_io/engine + itself only")


def test_no_underscore_name_crosses_tier_boundary() -> None:
    """Clause (h): a leading-underscore `ImportFrom` name never crosses a
    tier boundary, except when either endpoint is a SHIM or LEGACY module.
    """
    exempt_tiers = {"SHIM", "LEGACY"}
    bad: set[tuple[str, str]] = set()
    for raw in _RAW_IMPORTS:
        name = raw.imported_name
        if name is None or not name.startswith("_") or name.startswith("__"):
            continue
        si, di = classify(raw.src), classify(raw.dst)
        if si.tier == di.tier:
            continue  # no boundary crossed
        if si.tier in exempt_tiers or di.tier in exempt_tiers:
            continue
        bad.add((raw.src, raw.dst))
    _assert_no_violations(bad, rule="(h) underscore names never cross a tier boundary")


# --------------------------------------------------------------------------
# Ratchet integrity
# --------------------------------------------------------------------------


def test_pending_violations_allowlist_has_no_stale_entries() -> None:
    """The seeded allowlist may only shrink: every entry's edge must still exist."""
    stale = sorted(edge for edge in PENDING_VIOLATIONS if edge not in EDGES)
    assert not stale, (
        "PENDING_VIOLATIONS references edge(s) that no longer exist in the "
        f"current import graph — remove them, the ratchet has tightened: {stale}"
    )


def test_ratchet_is_flipped_allowlist_empty() -> None:
    """The ratchet is FLIPPED (v1 O14 / v2 O19): the import contract is a
    hard invariant. Adding a `PENDING_VIOLATIONS` entry requires a
    lead-modeller-approved work order naming the removal order — a red
    isolation suite is fixed by fixing the import, never by allowlisting."""
    assert PENDING_VIOLATIONS == {}, (
        "PENDING_VIOLATIONS must stay empty after the flip; found: "
        f"{PENDING_VIOLATIONS}"
    )
