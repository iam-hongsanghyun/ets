"""Carbon cap rule (T2 runtime, engine/host-facing).

``CCRCapRule`` (competitive per-year pipeline, ``core.protocols.CapRule``),
moved VERBATIM from ``solvers/ccr.py`` in the engine work order (v1 O8 /
v2 O12, ``docs/feature-modules-plan.md``). The mechanism, references, and
symbol table live in ``state.py``'s module docstring (the rule math is
``CCRState.cap_adjustment``). Wired by ``ets.engine.wiring`` — never
imported by other features or by ``config_io``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .state import CCRState

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pandas as pd

    from ...core.market.model import CarbonMarket


class CCRCapRule:
    r"""Carbon cap rule as a ``CapRule`` on the competitive per-year pipeline.

    Implements ``ets.core.protocols.CapRule`` (work order O5). ``pre_clear``
    is lifted VERBATIM from the per-year CCR block of the competitive
    pipeline (now ``core/ledger.py:simulate_path_details``; flag + start-year
    gating), ``post_clear`` from its post-clearing record block, so injected
    and inline behaviour are bit-identical.

    Algorithm:
        LaTeX:
        $$ \Delta Q_t^{CCR} = \phi_e \,\frac{e_{t-1} - \bar e}{\bar e}
                            + \phi_z \,\frac{z_{t-1} - \bar z}{\bar z} $$

        ASCII fallback:
            delta_q = phi_e*(e_prev - ebar)/ebar + phi_z*(z_prev - zbar)/zbar

        (Symbols and units: see the ``state.py`` module docstring; the
        signal is LAGGED — period-(t-1) realised emissions and abatement
        cost.)

    Split gating (economics, not symmetry — Arbitration outcomes / plan v2):

    * ``pre_clear`` requires the per-year ``ccr_enabled`` flag AND
      ``year >= ccr_start_year`` (non-numeric year labels leave the rule
      active): no cap adjustment before the rule exists.
    * ``post_clear`` requires the flag ONLY — NO start-year condition.
      Pre-start years still record e_t, z_t, so the first ACTIVE year prices
      the last pre-start year's outcomes (e_{t-1}, z_{t-1}) instead of
      starting blind, exactly as a regulator observes the market before the
      rule takes effect.

    Lifecycle: stateful across years within one path evaluation (the
    ``CCRState`` lagged aggregates); construct a fresh instance per
    evaluation (see ``ets.core.protocols`` module docstring).
    """

    def __init__(self, ccr_state: CCRState | None = None) -> None:
        self.ccr_state = ccr_state if ccr_state is not None else CCRState()

    def pre_clear(
        self, market: CarbonMarket, state: Mapping[str, float]
    ) -> tuple[float, dict[str, float]]:
        """Compute ΔQ_t from the lagged deviations (flag + start-year gated).

        Args:
            market: The year's market (``ccr_*`` fields).
            state: Beginning-of-year bank balances [Mt CO2e] — unused by the
                CCR (its lagged state is self-recorded), accepted per the
                ``CapRule`` protocol.

        Returns:
            ``(ccr_adjustment, diagnostics)`` with diagnostics keys
            ``ccr_adjustment`` / ``ccr_emissions_deviation`` /
            ``ccr_cost_deviation``.
        """
        ccr_adjustment = 0.0
        ccr_emissions_deviation = 0.0
        ccr_cost_deviation = 0.0

        ccr_active = getattr(market, "ccr_enabled", False)
        if ccr_active:
            try:
                ccr_active = float(str(market.year)) >= float(
                    getattr(market, "ccr_start_year", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                pass  # non-numeric year labels: rule active
        if ccr_active:
            ccr_adjustment, ccr_emissions_deviation, ccr_cost_deviation = (
                self.ccr_state.cap_adjustment(
                    phi_emissions=float(getattr(market, "ccr_phi_emissions", 0.0)),
                    phi_abatement_cost=float(
                        getattr(market, "ccr_phi_abatement_cost", 0.0)
                    ),
                    reference_emissions=float(
                        getattr(market, "ccr_reference_emissions", 0.0)
                    ),
                    reference_abatement_cost=float(
                        getattr(market, "ccr_reference_abatement_cost", 0.0)
                    ),
                    year_label=str(market.year),
                )
            )

        return ccr_adjustment, {
            "ccr_adjustment": ccr_adjustment,
            "ccr_emissions_deviation": ccr_emissions_deviation,
            "ccr_cost_deviation": ccr_cost_deviation,
        }

    def post_clear(self, market: CarbonMarket, participant_df: pd.DataFrame) -> None:
        """Record this year's realised aggregates as next year's signal.

        Gated by the per-year ``ccr_enabled`` flag ONLY — deliberately NO
        start-year condition (see class docstring): pre-start years
        accumulate the lagged signal.
        """
        if getattr(market, "ccr_enabled", False):
            self.ccr_state.record(
                emissions=float(participant_df["Residual Emissions"].sum()),
                abatement_cost=float(participant_df["Abatement Cost"].sum()),
            )
