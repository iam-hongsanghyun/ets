"""Deprecated mirror of ``pe.features.endogenous_investment.vintage`` — import ``pe.features.endogenous_investment.vintage`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.endogenous_investment.vintage import *  # noqa

warnings.warn(
    "ets.features.endogenous_investment.vintage is deprecated; import pe.features.endogenous_investment.vintage instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
