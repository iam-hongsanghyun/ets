r"""Gauss–Seidel path-map relaxation kernels (T0 core).

Pure helpers over *path maps* — mappings ``{key: value}`` from an opaque
path key (e.g. ``(scenario, year)``) to a scalar price — shared by the
soft-link coupling fixed-point loop (Feedback Option B,
:mod:`pe.coupling.loop`) and, forthcoming, the D2 joint-equilibrium outer
loop (``pe.engine.joint``). None of these functions carries coupling- or
engine-specific state: each is a pure function of its argument maps plus a
relaxation weight or reference scale, so this kernel is importable from
every higher tier (engine T3 may import core T0 but never coupling T4).

References:
    docs/joint-equilibrium.md §3 (damping), §5 (mixed-unit convergence
    norm); docs/joint-equilibrium-plan.md §5/§6 (work order D2-1).
"""

from __future__ import annotations

# Opaque path map: a hashable path key (e.g. (scenario, year)) -> scalar price.
PathMap = dict[tuple[str, str], float]


def max_pathmap_change(previous: PathMap, current: PathMap) -> float:
    keys = set(previous) | set(current)
    return max(
        (abs(current.get(k, 0.0) - previous.get(k, 0.0)) for k in keys),
        default=0.0,
    )


def max_pathmap_relative_change(previous: PathMap, current: PathMap, ref: float) -> float:
    r"""Per-market relative (dimensionless) path change, max over years.

    The D2 joint-equilibrium convergence norm for a single market's price
    path (docs/joint-equilibrium.md §5). Each year's absolute change is
    normalized by a per-market scale so that the result is dimensionless and
    can be maxed across mixed-unit markets:

        max over years t of  |P^k(t) − P^{k−1}(t)| / max(P_ref, |P^k(t)|)

    The ``max(P_ref, |P^k(t)|)`` denominator is the div-by-zero guard: with a
    positive reference scale ``ref`` (spec default: the market's max
    standalone price) the denominator never falls below ``ref``, so a market
    driven toward the oversupply boundary ``P → 0`` stays well-posed. The
    caller maxes this across the SCC's markets to get the scenario-level norm.

    Args:
        previous: Prior-iteration path map ``P^{k−1}`` (key -> price).
        current: Current-iteration path map ``P^k`` (key -> price).
        ref: Per-market reference scale ``P_ref`` [same unit as the prices],
            expected positive; floors the denominator to prevent division by
            zero as the current price approaches zero.

    Returns:
        The maximum, over the union of keys, of the reference-normalized
        absolute change; ``0.0`` for empty maps.
    """
    keys = set(previous) | set(current)
    return max(
        (
            abs(current.get(k, 0.0) - previous.get(k, 0.0)) / max(ref, abs(current.get(k, 0.0)))
            for k in keys
        ),
        default=0.0,
    )


def relax_pathmap(previous: PathMap, current: PathMap, weight: float) -> PathMap:
    r"""Under-relax the price signal: (1-w)·previous + w·current, key by key.

    Algorithm:
        LaTeX:
        $$ P_{\text{next}} = (1 - w)\,P_{\text{prev}} + w\,P_{\text{cur}} $$

        ASCII fallback:
            P_next = (1 - w) * P_prev + w * P_cur

        Symbols (units):
            P_prev : prior-iteration price at a key [currency/tCO2]
            P_cur  : current-iteration price at a key [currency/tCO2]
            w      : relaxation weight [dimensionless], w ∈ (0, 1]; w = 1 is
                     a plain (undamped) Gauss–Seidel step, w < 1 damps
                     oscillation in the fixed-point iteration.
            P_next : relaxed price fed to the next iteration [currency/tCO2]
    """
    keys = set(previous) | set(current)
    return {
        k: (1.0 - weight) * previous.get(k, current.get(k, 0.0))
        + weight * current.get(k, previous.get(k, 0.0))
        for k in keys
    }
