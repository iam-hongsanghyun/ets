# Backward-compatibility shim — re-exports from the config_io sub-package.
# New location: src/ets/config_io/.
import warnings

from .config_io import (
    normalize_year,
    build_market_from_year,
    build_markets_from_config,
    build_markets_from_file,
    load_config,
    save_config,
    normalize_config,
    normalize_scenario,
    normalize_participant,
    normalize_technology_option,
    build_participant,
    build_technology_option,
    blank_config,
    blank_scenario,
    blank_year_config,
    blank_participant,
    blank_technology_option,
    _interp_value,
    _interp_ratio,
    _normalize_trajectory,
)

warnings.warn(
    "ets.scenarios is deprecated; import from ets.config_io instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "normalize_year",
    "build_market_from_year",
    "build_markets_from_config",
    "build_markets_from_file",
    "load_config",
    "save_config",
    "normalize_config",
    "normalize_scenario",
    "normalize_participant",
    "normalize_technology_option",
    "build_participant",
    "build_technology_option",
    "blank_config",
    "blank_scenario",
    "blank_year_config",
    "blank_participant",
    "blank_technology_option",
    "_interp_value",
    "_interp_ratio",
    "_normalize_trajectory",
]
