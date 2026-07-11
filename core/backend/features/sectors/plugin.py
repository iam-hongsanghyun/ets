r"""Sectors plugin door — pool transform + summary reporter (T2).

Two-door feature (``docs/feature-modules-plan.md`` PLAN v2 §"Two-door
features"): this module is the ONLY thing ``config_io`` may import from
``ets.features.sectors``. Sectors has no runtime module — it is "attributes
+ aggregation + normalization" (v1 §1 "Features challenged / merged"; v2
feature verdicts: "sectors (transform + summary reporter)"). It never
imports another feature, and imports only ``ets.core.*`` + stdlib (never
``config_io`` — the trajectory-interpolation helper the pool math needs is
INJECTED by the host, see ``derive_sector_pools``).

Two build-time pieces (Arbitration outcomes, O9):

* ``derive_sector_pools`` — the scenario-level pool derivation / cap-auction
  override, a HOST-CALLED function (not a per-participant
  ``ParticipantTransform``): it runs ONCE per (scenario, year), before the
  per-participant pipeline, because the pool table depends on ALL of the
  year's participants (the ``initial_emissions`` fallback sum), not one at a
  time. Relocated VERBATIM from the pre-refactor
  ``config_io/builder.py`` "Sector-level derivation" block (lines 387-406 of
  ``build_market_from_year``, the pool/derived-cap/derived-auction loop).
* ``SectorPoolAllocation`` — the per-participant free-allocation-ratio patch,
  a ``core.protocols.ParticipantTransform``. Relocated VERBATIM from the
  same block's participant loop (lines 408-423). Reads the pool table
  ``derive_sector_pools`` computed, via ``meta["sector_pools"]`` (the host
  folds the per-year pool table into the ``meta`` mapping it passes down the
  ``_PARTICIPANT_TRANSFORMS`` pipeline — see ``config_io/builder.py``).

``SectorSummaryReporter`` (unchanged, O7) is relocated VERBATIM from the
pre-refactor ``core/market/reporting.py`` results.py:247-278 (sector-group
aggregate rows, then the per-sector compliance-cost percentile
distribution). It reads the ``"Sector Group"`` column ``config_io/builder.py``
stamps onto each participant and the columns other attach-always reporters
(CBAM) write onto the participant frame.

References:
    docs/feature-modules-plan.md — PLAN v2 §"Two-door features", "Feature
    verdicts v2"; Arbitration outcomes (O7, O9 binding conditions).
    core/protocols.py — ``ParticipantTransform``, ``SummaryReporter``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import pandas as pd

    from ...core.market.model import CarbonMarket

__all__ = ["SectorPoolAllocation", "SectorSummaryReporter", "derive_sector_pools"]


def derive_sector_pools(
    year_num: float,
    sectors: list[dict[str, Any]],
    participants: list[dict[str, Any]],
    interp_value: Callable[[float, dict[str, Any]], float | None],
) -> tuple[dict[str, float], float | None, float | None]:
    r"""Derive per-sector free-allocation pools and the scenario cap/auction totals.

    Algorithm:
        LaTeX (per sector :math:`s`):
        $$ Q_s = \mathrm{interp}\big(t,\,\mathrm{cap\_trajectory}_s\big)
           \;\;\text{or}\;\; \sum_{i \,:\, \mathrm{sector}(i) = s} e_{0,i}
           \quad\text{(fallback)} $$
        $$ A_s = Q_s \cdot \mathrm{interp}\big(t,\,
           \mathrm{auction\_share\_trajectory}_s\big) $$
        $$ \mathrm{pool}_s = Q_s - A_s, \qquad
           \overline{Q} = \sum_s Q_s, \qquad \overline{A} = \sum_s A_s $$

        ASCII fallback:
            scap = interp_value(year_num, sector["cap_trajectory"])
                   or sum(initial_emissions of participants in this sector)
            sauc_share = interp_value(year_num, sector["auction_share_trajectory"]) or 0.0
            sauc = scap * sauc_share
            sector_pools[sector["name"]] = scap - sauc
            derived_total_cap += scap
            derived_auction  += sauc

        Symbols (units):
            t            : year_num, numeric scenario year                [yr]
            Q_s          : sector s's derived cap (``scap``)          [Mt CO2e]
            A_s          : sector s's derived auction volume (``sauc``)
                                                                        [Mt CO2e]
            pool_s       : sector s's free-allocation pool (cap - auction)
                                                                        [Mt CO2e]
            e_{0,i}      : participant i's ``initial_emissions``       [Mt CO2e]
            Qbar, Abar   : scenario-level derived ``total_cap`` /
                           ``auction_offered``                         [Mt CO2e]

    A sector with no configured ``cap_trajectory`` falls back to summing
    ``initial_emissions`` over every participant whose ``sector_group``
    matches the sector's ``name`` (the original guard, preserved verbatim).
    Returns ``({}, None, None)`` when ``sectors`` is empty — the scenario has
    no sector-derived cap/auction override (the pre-refactor ``if sectors:``
    branch, preserved as an early return).

    This is a HOST-CALLED function, not a ``ParticipantTransform``
    (Arbitration outcomes, O9: "the pool math may stay a host-called plugin
    function rather than a per-participant transform"): it computes ONE pool
    table per (scenario, year), before the per-participant pipeline runs —
    the ``initial_emissions`` fallback needs every participant in the year at
    once, which a per-participant transform's ``(raw, year_num, meta)``
    signature cannot see. The host folds the returned ``sector_pools`` table
    into the ``meta`` mapping it passes to ``SectorPoolAllocation.apply`` for
    every participant in the same year.

    Args:
        year_num: Numeric scenario year (e.g. ``2031.0``).
        sectors: The scenario's normalized ``sectors`` list; each a dict with
            ``"name"``, ``"cap_trajectory"``, ``"auction_share_trajectory"``.
        participants: The year's raw participant dicts (read-only; used only
            for the per-sector ``initial_emissions`` fallback sum).
        interp_value: The host's trajectory-interpolation function
            (``config_io/builder.py`` ``_interp_value``), INJECTED so this
            feature module never imports ``config_io`` (T2 imports T0 +
            stdlib only).

    Returns:
        ``(sector_pools, derived_total_cap, derived_auction)`` — the
        per-sector free-allocation pool table [Mt CO2e] keyed by sector name,
        and the scenario's derived ``total_cap`` / ``auction_offered``
        [Mt CO2e] (``None`` for both when ``sectors`` is empty).
    """
    if not sectors:
        return {}, None, None

    sector_pools: dict[str, float] = {}
    _derived_total_cap = 0.0
    _derived_auction = 0.0
    for s in sectors:
        sname = s["name"]
        scap = interp_value(year_num, s.get("cap_trajectory") or {})
        if scap is None:
            # Fall back to summing participant initial_emissions for this sector
            scap = sum(
                float(p.get("initial_emissions", 0))
                for p in participants
                if str(p.get("sector_group", "")) == sname
            )
        sauc_share = interp_value(year_num, s.get("auction_share_trajectory") or {}) or 0.0
        sauc = scap * sauc_share
        sector_pools[sname] = scap - sauc
        _derived_total_cap += scap
        _derived_auction += sauc
    return sector_pools, _derived_total_cap, _derived_auction


class SectorPoolAllocation:
    r"""Per-participant free-allocation ratio derived from its sector's pool.

    Algorithm:
        LaTeX:
        $$ r_{\mathrm{free},i} = \min\!\left(1,\;
           \frac{\mathrm{pool}_{s(i)} \cdot \sigma_i}{e_{0,i}}\right) $$

        ASCII fallback:
            allocated_mt = sector_pools[sector_group] * sector_allocation_share
            free_allocation_ratio = min(1.0, allocated_mt / initial_emissions)

        Symbols (units):
            pool_{s(i)}  : participant i's sector pool, from
                           ``derive_sector_pools`` via
                           ``meta["sector_pools"]``                   [Mt CO2e]
            sigma_i      : ``sector_allocation_share``, dimensionless (0-1)
            e_{0,i}      : ``initial_emissions``                      [Mt CO2e]
            r_free,i     : ``free_allocation_ratio``, dimensionless (0-1)

    Active only when the participant's ``sector_group`` has an entry in the
    host-supplied pool table AND ``sector_allocation_share`` and
    ``initial_emissions`` are both strictly positive (the original guard,
    preserved verbatim); participants outside any sector, or with a zero /
    unset share, pass through unchanged. A scenario with no sectors
    configured supplies an EMPTY pool table (``derive_sector_pools`` returns
    ``{}``), so every participant takes the pass-through branch — reproducing
    the pre-refactor ``if sectors: ... else: raw_participants = list(...)``
    split as one uniform code path.

    Declared fields (``core/protocols.py`` ``ParticipantTransform``
    declared-fields discipline):
        Reads: ``sector_group``, ``sector_allocation_share``,
            ``initial_emissions``; ``meta["sector_pools"]`` (the host-derived
            pool table from ``derive_sector_pools`` — NOT a raw participant
            field).
        Writes: ``free_allocation_ratio`` (overwritten downstream by OBA when
            both are configured for the same participant — Arbitration
            outcomes, O9; see ``features.oba.plugin.OBABenchmarkAllocation``).
    """

    def apply(
        self, raw: dict[str, Any], year_num: float, meta: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Override ``free_allocation_ratio`` from the sector pool, if configured.

        Args:
            raw: The participant's raw config dict for this year. Not
                mutated.
            year_num: Unused (the pool table is precomputed by the host for
                this year); accepted only for ``ParticipantTransform``
                conformance.
            meta: Scenario-level mapping; must carry ``"sector_pools"`` (the
                table ``derive_sector_pools`` returned for this year).

        Returns:
            A new dict with ``free_allocation_ratio`` overridden when the
            participant's sector has a pool and its share/emissions are
            positive; ``raw`` itself (unchanged) otherwise.
        """
        sector_pools = meta.get("sector_pools") or {}
        sg = str(raw.get("sector_group", ""))
        sas = float(raw.get("sector_allocation_share", 0.0) or 0.0)
        ie = float(raw.get("initial_emissions", 0) or 0)
        if sg in sector_pools and sas > 0 and ie > 0:
            pool = sector_pools[sg]
            allocated_mt = pool * sas
            derived_ratio = min(1.0, allocated_mt / ie)
            return {**raw, "free_allocation_ratio": derived_ratio}
        return raw


class SectorSummaryReporter:
    r"""Sector-group aggregate columns and compliance-cost percentiles.

    Algorithm:
        LaTeX (per sector group :math:`g`, participants :math:`i \in g`):
        $$ \mathrm{AuctionRevenueShare}_g = R_{\mathrm{auction}} \cdot
           \frac{\sum_{i \in g} \mathrm{buys}_i}{\sum_i \mathrm{buys}_i} $$
        $$ P_{k,g} = \mathrm{percentile}\big(\{c_i : i \in g\},\, k\big),
           \quad k \in \{10, 50, 90\} $$
        $$ \sigma_g = \mathrm{std}\big(\{c_i : i \in g\}\big) $$

        ASCII fallback:
            sector_buys        = sum(buys_i for i in group g)
            total_buys         = sum(buys_i for i in all participants)
            auction_rev_share  = auction_rev * (sector_buys / total_buys)
            p10, p50, p90      = np.percentile(costs_g, [10, 50, 90])
            cost_std_dev       = np.std(costs_g)

        Symbols (units):
            R_auction    : scenario ``"Total Auction Revenue"``  [currency]
            buys_i       : participant i's ``"Allowance Buys"``  [Mt CO2e]
            c_i          : participant i's ``"Total Compliance Cost"``
                                                                    [currency]
            P_{k,g}      : group g's k-th percentile of c_i        [currency]
            sigma_g      : group g's compliance-cost std. dev.     [currency]

    Percentiles and the std. dev. are only computed for groups with >= 2
    participants (a percentile / std. dev. of one observation is not
    meaningful — the original guard, preserved verbatim).

    Reporters are ATTACH-ALWAYS (``core/protocols.py`` ``SummaryReporter``):
    a scenario without a ``"Sector Group"`` column contributes no columns
    (the original guard), which is the neutral (no sectors configured) case.
    """

    def contribute(
        self,
        summary: dict[str, float | str],
        market: "CarbonMarket",
        participant_df: "pd.DataFrame",
        price: float,
    ) -> None:
        """Append per-sector aggregate and percentile columns to the summary.

        Args:
            summary: The accumulating summary dict — read for
                ``"Total Auction Revenue"`` and mutated in place.
            market: The year's market (unused directly; kept for protocol
                conformance).
            participant_df: The year's solved participant results frame
                (must carry ``"Sector Group"`` for any columns to be added).
            price: The year's delivered allowance price [currency/tCO2]
                (unused directly).
        """
        # ── Sector-group aggregates ──────────────────────────────────────
        if "Sector Group" in participant_df.columns:
            for sg, grp in participant_df.groupby("Sector Group"):
                if not sg:
                    continue
                summary[f"{sg} Total Abatement"]           = float(grp["Abatement"].sum())
                summary[f"{sg} Total Compliance Cost"]      = float(grp["Total Compliance Cost"].sum())
                summary[f"{sg} Total CBAM Liability"]       = float(grp["CBAM Liability"].sum())
                # Auction revenue attribution: sector's share of total allowance buys × auction price
                sector_buys = float(grp["Allowance Buys"].sum())
                total_buys  = float(participant_df["Allowance Buys"].sum())
                auction_rev = summary.get("Total Auction Revenue", 0.0)
                summary[f"{sg} Allowance Buys"]             = sector_buys
                summary[f"{sg} Allowance Cost"]             = float(grp["Allowance Cost"].sum())
                summary[f"{sg} Auction Revenue Share"]      = (
                    float(auction_rev) * (sector_buys / total_buys) if total_buys > 0 else 0.0
                )
                # Scope 2 by sector
                if "Indirect Emissions" in grp.columns:
                    summary[f"{sg} Indirect Emissions"]     = float(grp["Indirect Emissions"].sum())
                    summary[f"{sg} Scope 2 CBAM Liability"] = float(grp["Scope 2 CBAM Liability"].sum())

        # ── Per-sector compliance cost distribution (P10, P50, P90) ──────
        if "Sector Group" in participant_df.columns:
            for sg, grp in participant_df.groupby("Sector Group"):
                if not sg or len(grp) < 2:
                    continue
                costs = grp["Total Compliance Cost"].values
                summary[f"{sg} P10 Compliance Cost"] = float(np.percentile(costs, 10))
                summary[f"{sg} P50 Compliance Cost"] = float(np.percentile(costs, 50))
                summary[f"{sg} P90 Compliance Cost"] = float(np.percentile(costs, 90))
                summary[f"{sg} Cost Std Dev"] = float(np.std(costs))
