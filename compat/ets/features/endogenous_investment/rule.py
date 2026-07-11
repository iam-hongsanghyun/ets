"""Deprecated mirror of ``pe.features.endogenous_investment.rule`` — import ``pe.features.endogenous_investment.rule`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.endogenous_investment.rule import *  # noqa

warnings.warn(
    "ets.features.endogenous_investment.rule is deprecated; import pe.features.endogenous_investment.rule instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
