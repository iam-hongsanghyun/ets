"""Builder host-pipeline regression gate (O9 fast gate).

Guards the equivalence argument for O9 (sector-pool + OBA build-time
transform extraction, `docs/feature-modules-plan.md` work order O9): the
per-participant preparation in `config_io.builder.build_market_from_year` is
an explicit host pipeline of `ParticipantTransform` steps
(`config_io.builder._PARTICIPANT_TRANSFORMS`) composed in a reviewed source
literal, with the two binding Arbitration-outcomes pins:

* OBA runs AFTER the trajectory patch — it reads the trajectory-PATCHED
  `initial_emissions`, not the raw config value.
* OBA's write to `free_allocation_ratio` OVERWRITES whatever the sectors
  pool-allocation step wrote for the same participant (a documented
  cross-feature coupling through the raw-dict medium).

`tests/test_golden_baselines.py` proves the full-scenario cell values are
unchanged bit-exactly; this file is the fast, closed-form pin on the
pipeline's shape and the two ordering pins, in seconds rather than a full
golden replay.
"""

from __future__ import annotations

import copy

from ets.config_io.builder import _PARTICIPANT_TRANSFORMS, build_market_from_year
from ets.config_io.templates import blank_participant, blank_year_config


def _year_config(participants: list[dict]) -> dict:
    """One year_config with `derive_from_cap` auctioning, ample headroom."""
    year = blank_year_config()
    year.update(
        {
            "year": "2032",
            "total_cap": 1_000.0,
            "auction_mode": "derive_from_cap",
            "price_lower_bound": 0.0,
            "price_upper_bound": 200.0,
            "participants": participants,
        }
    )
    return year


def _participant(**overrides: object) -> dict:
    p = blank_participant()
    p.update(
        {
            "name": "P1",
            "penalty_price": 100.0,
            "abatement_type": "linear",
            "cost_slope": 2.0,
            "max_abatement": 10.0,
        }
    )
    p.update(overrides)
    return p


# ── (a) literal pin: exact names and order of _PARTICIPANT_TRANSFORMS ───────


def test_participant_transforms_literal_pin() -> None:
    """`_PARTICIPANT_TRANSFORMS` is sectors -> trajectory patch -> OBA, exactly."""
    names = [step.__qualname__ for step in _PARTICIPANT_TRANSFORMS]
    assert names == [
        "SectorPoolAllocation.apply",
        "_patch_trajectories",
        "OBABenchmarkAllocation.apply",
    ]


# ── (b) OBA-after-trajectory: reads the PATCHED initial_emissions ───────────


def test_oba_reads_trajectory_patched_initial_emissions() -> None:
    """OBA's implied free allocation uses the trajectory-patched `initial_emissions`.

    year_num = 2032, trajectory linearly interpolates initial_emissions from
    100.0 (2030) to 60.0 (2034): frac = (2032-2030)/(2034-2030) = 0.5, so the
    patched value is 100 + 0.5*(60-100) = 80.0 — NOT the raw config value of
    100.0. The OBA ratio is a closed form on whichever value it reads:
    free_alloc_mt = benchmark_emission_intensity * production_output = 4.0 * 10.0 = 40.0
    ratio_from_patched = min(1, 40.0 / 80.0) = 0.5
    ratio_from_raw     = min(1, 40.0 / 100.0) = 0.4   (would be the bug)
    """
    participant = _participant(
        initial_emissions=100.0,
        initial_emissions_trajectory={
            "start_year": "2030",
            "end_year": "2034",
            "start_value": 100.0,
            "end_value": 60.0,
        },
        free_allocation_ratio=0.0,
        production_output=10.0,
        benchmark_emission_intensity=4.0,
    )
    market = build_market_from_year("O9 pin", _year_config([participant]))

    assert market.participants[0].initial_emissions == 80.0
    assert market.participants[0].free_allocation_ratio == 0.5


# ── (c) OBA-overwrites-sectors: OBA wins the cross-feature coupling ─────────


def test_oba_overwrites_sector_pool_ratio() -> None:
    """A participant with BOTH sector allocation and OBA fields ends on the OBA ratio.

    Sector "Steel" has no cap_trajectory, so its pool falls back to summing
    initial_emissions of Steel participants (just P1: 100.0), with a zero
    auction share -> pool = 100.0. sector_allocation_share = 1.0, so the
    sectors step alone would derive ratio = min(1, 100*1.0/100) = 1.0.
    OBA fields (benchmark_emission_intensity=0.3, production_output=10.0)
    imply free_alloc_mt = 3.0 -> OBA ratio = min(1, 3.0/100) = 0.03, which
    must be the FINAL ratio (OBA runs after and overwrites).
    """
    participant = _participant(
        sector_group="Steel",
        sector_allocation_share=1.0,
        initial_emissions=100.0,
        free_allocation_ratio=0.0,
        production_output=10.0,
        benchmark_emission_intensity=0.3,
    )
    scenario_meta = {
        "sectors": [
            {"name": "Steel", "cap_trajectory": {}, "auction_share_trajectory": {}}
        ]
    }
    market = build_market_from_year("O9 pin", _year_config([participant]), scenario_meta)

    assert market.participants[0].free_allocation_ratio == 0.03


def test_sector_pool_ratio_applies_when_oba_not_configured() -> None:
    """Sanity check on the fixture: without OBA fields, the sector ratio survives."""
    participant = _participant(
        sector_group="Steel",
        sector_allocation_share=1.0,
        initial_emissions=100.0,
        free_allocation_ratio=0.0,
    )
    scenario_meta = {
        "sectors": [
            {"name": "Steel", "cap_trajectory": {}, "auction_share_trajectory": {}}
        ]
    }
    market = build_market_from_year("O9 pin", _year_config([participant]), scenario_meta)

    assert market.participants[0].free_allocation_ratio == 1.0


# ── (d) purity: no transform mutates its `raw` argument ─────────────────────


def test_participant_transforms_do_not_mutate_raw() -> None:
    """Every `_PARTICIPANT_TRANSFORMS` step leaves its `raw` argument untouched.

    `core.protocols.ParticipantTransform`'s purity contract: `apply` never
    mutates `raw`, it returns a NEW dict (or `raw` itself when nothing
    changed). Exercised with a participant that is active for every step
    (sector pool AND OBA both configured) so no step takes an early,
    trivially-pure return path.
    """
    raw = _participant(
        sector_group="Steel",
        sector_allocation_share=1.0,
        initial_emissions=100.0,
        initial_emissions_trajectory={
            "start_year": "2030",
            "end_year": "2034",
            "start_value": 100.0,
            "end_value": 60.0,
        },
        grid_emission_factor=0.5,
        grid_emission_factor_trajectory={
            "start_year": "2030",
            "end_year": "2034",
            "start_value": 0.5,
            "end_value": 0.2,
        },
        production_output=10.0,
        benchmark_emission_intensity=0.3,
    )
    meta: dict = {"sector_pools": {"Steel": 100.0}}

    for transform in _PARTICIPANT_TRANSFORMS:
        snapshot = copy.deepcopy(raw)
        transform(raw, 2032.0, meta)
        assert raw == snapshot, f"{transform.__qualname__} mutated its `raw` argument"
