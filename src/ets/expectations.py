# Backward-compatibility shim — re-exports from solvers.expectations.
# New location: src/ets/solvers/expectations.py.
import warnings

from .solvers.expectations import (
    ALLOWED_EXPECTATION_RULES,
    ExpectationSpec,
    expectation_sort_key,
    validate_expectation_rule,
    build_expectation_specs,
    derive_expected_prices,
)

warnings.warn(
    "ets.expectations is deprecated; import from ets.solvers.expectations instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ALLOWED_EXPECTATION_RULES",
    "ExpectationSpec",
    "expectation_sort_key",
    "validate_expectation_rule",
    "build_expectation_specs",
    "derive_expected_prices",
]
