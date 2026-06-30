"""External-model adapters for Feedback Option B (soft-link coupling).

An adapter maps the latest ETS carbon-price path to a revised scenario config
(typically updated per-participant ``initial_emissions``) for the next ETS run.
Plug in your own by implementing the :class:`ExternalModel` protocol — wrap a
PyPSA dispatch, a CGE, a DSGE, or any responder behind ``respond``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol, runtime_checkable

PriceMap = dict[tuple[str, str], float]


@runtime_checkable
class ExternalModel(Protocol):
    """Adapter contract for an external model coupled to the ETS engine."""

    def respond(
        self, baseline_config: dict, prices: PriceMap, iteration: int
    ) -> dict:
        """Return a NEW scenario config given the latest carbon-price path.

        Parameters
        ----------
        baseline_config : dict
            The ORIGINAL (iteration-0) config. Always derive from this so the
            mapping is price → activity (not a compounding adjustment).
        prices : dict[(scenario_name, year_label) -> price]
            Carbon price from the most recent ETS run.
        iteration : int
            1-based coupling iteration (for logging / schedules).

        Returns
        -------
        dict
            A config of identical shape with revised activity (e.g. updated
            ``initial_emissions`` per participant per year).
        """
        ...


class NullExternalModel:
    """Identity adapter — no feedback. The loop converges in one iteration.

    Useful as a control: coupling with this adapter must reproduce a plain
    :func:`ets.solvers.run_simulation_from_config` run.
    """

    def respond(self, baseline_config: dict, prices: PriceMap, iteration: int) -> dict:
        return deepcopy(baseline_config)


class ElasticityExternalModel:
    r"""Reference adapter: activity responds to the carbon price by elasticity.

    A self-contained stand-in for a real energy/macro model — it needs no extra
    dependencies, so the coupling loop is runnable out of the box. Each
    participant's baseline scales by a constant-elasticity activity response:

    Algorithm:
        LaTeX:  $E^{(k+1)}_{i,t} = E^{0}_{i,t}\,
                 \left(\frac{\max(P_{t}, P_\mathrm{floor})}{P_\mathrm{ref}}\right)^{-\varepsilon}$
        ASCII:  E_next = E0 * (max(P, P_floor) / P_ref) ** (-eps)

    The multiplier is clamped to ``[min_multiplier, max_multiplier]`` for
    numerical safety (a constant-elasticity curve is unbounded as P → 0). This
    is the OUTER-LOOP analogue of Feedback Option A's within-clearing baseline;
    with matching parameters the two converge to a similar fixed point.

    Parameters
    ----------
    elasticity : float
        ε ≥ 0, the price elasticity of carbon-intensive activity.
    reference_price : float
        P_ref > 0, the price at which activity equals its nominal baseline.
    price_floor : float
        Lower clamp on the price used in the ratio (avoids the P → 0 blow-up).
    min_multiplier, max_multiplier : float
        Bounds on the activity multiplier.
    """

    def __init__(
        self,
        elasticity: float,
        reference_price: float,
        price_floor: float = 1.0,
        min_multiplier: float = 0.0,
        max_multiplier: float = 2.0,
    ) -> None:
        if elasticity < 0:
            raise ValueError("elasticity must be non-negative.")
        if reference_price <= 0:
            raise ValueError("reference_price must be positive.")
        if price_floor <= 0:
            raise ValueError("price_floor must be positive.")
        if not 0.0 <= min_multiplier <= max_multiplier:
            raise ValueError("require 0 <= min_multiplier <= max_multiplier.")
        self.elasticity = float(elasticity)
        self.reference_price = float(reference_price)
        self.price_floor = float(price_floor)
        self.min_multiplier = float(min_multiplier)
        self.max_multiplier = float(max_multiplier)

    def multiplier(self, price: float) -> float:
        effective_price = max(self.price_floor, float(price))
        raw = (effective_price / self.reference_price) ** (-self.elasticity)
        return min(self.max_multiplier, max(self.min_multiplier, raw))

    def respond(self, baseline_config: dict, prices: PriceMap, iteration: int) -> dict:
        updated = deepcopy(baseline_config)
        for scenario in updated.get("scenarios", []):
            scenario_name = str(scenario.get("name", ""))
            for year in scenario.get("years", []):
                year_label = str(year.get("year", ""))
                price = prices.get((scenario_name, year_label))
                if price is None:
                    continue
                m = self.multiplier(price)
                for participant in year.get("participants", []):
                    base = baseline_emissions(baseline_config, scenario_name, year_label, participant["name"])
                    if base is not None:
                        participant["initial_emissions"] = base * m
        return updated


def baseline_emissions(
    baseline_config: dict, scenario_name: str, year_label: str, participant_name: str
) -> float | None:
    """Look up a participant's nominal baseline emissions in the original config."""
    for scenario in baseline_config.get("scenarios", []):
        if str(scenario.get("name", "")) != scenario_name:
            continue
        for year in scenario.get("years", []):
            if str(year.get("year", "")) != year_label:
                continue
            for participant in year.get("participants", []):
                if participant.get("name") == participant_name:
                    return float(participant.get("initial_emissions", 0.0))
    return None
