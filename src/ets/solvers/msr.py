"""
Market Stability Reserve (MSR) for ETS.

The MSR is a non-linear supply-adjustment mechanism that:
  - WITHHOLDS allowances from auction when the total banked volume is too high
    (excessive surplus → deflationary price pressure)
  - RELEASES previously withheld allowances when the bank is too low
    (shortage → inflationary price pressure)

Rule (applied before each year's auction):

    if total_bank > upper_threshold:
        withheld = min(msr_withhold_rate × auction_offered, auction_offered)
        reserve_pool += withheld
        effective_auction -= withheld

    elif total_bank < lower_threshold and reserve_pool > 0:
        released = min(msr_release_rate, reserve_pool)
        reserve_pool -= released
        effective_auction += released

The reserve_pool accumulates withheld allowances and persists across years.
Allowances cancelled by the MSR (if msr_cancel_excess=True) are permanently
removed once the pool exceeds msr_cancel_threshold.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# Moved to core.defaults (O1); re-exported so this module's surface is unchanged.
from ..core.defaults import MSR_DEFAULTS  # noqa: F401

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pandas as pd

    from ..core.market.model import CarbonMarket

logger = logging.getLogger(__name__)


class MSRState:
    """
    Mutable state object carried across years for a single scenario.
    """

    def __init__(self, initial_reserve: float = 0.0) -> None:
        self.reserve_pool: float = float(initial_reserve)

    def apply(
        self,
        total_bank: float,
        auction_offered: float,
        upper_threshold: float,
        lower_threshold: float,
        withhold_rate: float,
        release_rate: float,
        cancel_excess: bool = False,
        cancel_threshold: float = 0.0,
        year_label: str = "",
    ) -> tuple[float, float, float]:
        """
        Apply MSR rule and return adjusted auction volume.

        Returns
        -------
        effective_auction : float   – auction supply after MSR adjustment
        withheld          : float   – Mt withheld this year (0 if no withholding)
        released          : float   – Mt released this year (0 if no release)
        """
        withheld = 0.0
        released = 0.0

        if total_bank > upper_threshold:
            withheld = min(withhold_rate * auction_offered, auction_offered)
            self.reserve_pool += withheld
            logger.debug(
                f"MSR [{year_label}]: bank={total_bank:.1f} > upper={upper_threshold:.1f} "
                f"→ withheld {withheld:.1f} Mt, pool now {self.reserve_pool:.1f} Mt"
            )

        elif total_bank < lower_threshold and self.reserve_pool > 0.0:
            released = min(release_rate, self.reserve_pool)
            self.reserve_pool -= released
            logger.debug(
                f"MSR [{year_label}]: bank={total_bank:.1f} < lower={lower_threshold:.1f} "
                f"→ released {released:.1f} Mt, pool now {self.reserve_pool:.1f} Mt"
            )

        # Optional: cancel allowances that have been in the pool too long
        if cancel_excess and self.reserve_pool > cancel_threshold:
            cancelled = self.reserve_pool - cancel_threshold
            self.reserve_pool = cancel_threshold
            logger.debug(
                f"MSR [{year_label}]: pool cancellation {cancelled:.1f} Mt "
                f"(pool > cancel_threshold {cancel_threshold:.1f})"
            )

        effective_auction = max(0.0, auction_offered - withheld + released)
        return effective_auction, withheld, released


class MSRCapRule:
    r"""Bank-threshold MSR as a ``CapRule`` on the competitive per-year pipeline.

    Implements ``ets.core.protocols.CapRule`` (work order O5). The rule body
    is lifted VERBATIM from the per-year MSR block of
    ``solvers/simulation.py:_simulate_path_details`` (the ``msr_active``
    gate + ``MSRState.apply`` call + the F1-fixed additive net adjustment),
    so injected and inline behaviour are bit-identical.

    Algorithm:
        LaTeX:
        $$ \Delta Q_t^{MSR} = r_t - w_t \qquad
           Q_t = \overline{Q}_t + \Delta Q_t^{CCR} + \Delta Q_t^{MSR} $$

        ASCII fallback:
            delta_q = released - withheld;  effective_carry += delta_q

        Symbols (units):
            w_t : MSR withholding from auction in year t   [Mt CO2e]
            r_t : MSR release from the reserve pool        [Mt CO2e]

    Gating: ``pre_clear`` requires the per-year ``msr_enabled`` flag AND
    ``year >= msr_start_year`` (non-numeric year labels leave the rule
    active). ``post_clear`` is a no-op — the bank the MSR reads is host
    state (beginning-of-year bank balances), not rule-recorded state.

    Lifecycle: stateful across years within one path evaluation (the
    ``MSRState`` reserve pool); construct a fresh instance per evaluation
    (see ``ets.core.protocols`` module docstring).
    """

    def __init__(self, msr_state: MSRState | None = None) -> None:
        self.msr_state = msr_state if msr_state is not None else MSRState()

    def pre_clear(
        self, market: CarbonMarket, state: Mapping[str, float]
    ) -> tuple[float, dict[str, float]]:
        """Withhold/release against the beginning-of-year bank; return the net.

        Args:
            market: The year's market (``msr_*`` fields).
            state: Beginning-of-year bank balances by participant [Mt CO2e].

        Returns:
            ``(msr_net, diagnostics)`` with ``msr_net = released - withheld``
            [Mt CO2e] and diagnostics keys ``msr_withheld`` / ``msr_released``
            / ``msr_pool``.
        """
        msr_withheld = 0.0
        msr_released = 0.0
        msr_pool = 0.0

        msr_active = getattr(market, "msr_enabled", False)
        if msr_active:
            try:
                msr_active = float(str(market.year)) >= float(
                    getattr(market, "msr_start_year", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                pass  # non-numeric year labels: rule active
        if msr_active:
            total_bank = sum(state.values())
            _, msr_withheld, msr_released = self.msr_state.apply(
                total_bank=total_bank,
                auction_offered=market.auction_offered,
                upper_threshold=float(
                    getattr(market, "msr_upper_threshold", MSR_DEFAULTS["msr_upper_threshold"])
                ),
                lower_threshold=float(
                    getattr(market, "msr_lower_threshold", MSR_DEFAULTS["msr_lower_threshold"])
                ),
                withhold_rate=float(
                    getattr(market, "msr_withhold_rate", MSR_DEFAULTS["msr_withhold_rate"])
                ),
                release_rate=float(
                    getattr(market, "msr_release_rate", MSR_DEFAULTS["msr_release_rate"])
                ),
                cancel_excess=bool(getattr(market, "msr_cancel_excess", False)),
                cancel_threshold=float(
                    getattr(market, "msr_cancel_threshold", MSR_DEFAULTS["msr_cancel_threshold"])
                ),
                year_label=str(market.year),
            )
            msr_pool = self.msr_state.reserve_pool

        # Inject the MSR net adjustment as carry-forward so solve_equilibrium
        # sees it (released adds to supply, withheld subtracts; the adjusted
        # auction volume returned by apply() is deliberately unused).
        # Compose additively with any CCR cap adjustment already applied:
        #   Q_t = Qbar + ΔQ_t^CCR + ΔQ_t^MSR   (F1 fix, blocks-composition-rules §0)
        msr_net = msr_released - msr_withheld
        return msr_net, {
            "msr_withheld": msr_withheld,
            "msr_released": msr_released,
            "msr_pool": msr_pool,
        }

    def post_clear(self, market: CarbonMarket, participant_df: pd.DataFrame) -> None:
        """No-op: the MSR reads host bank state, not rule-recorded state."""
