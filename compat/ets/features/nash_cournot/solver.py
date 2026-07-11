"""Deprecated mirror of ``pe.features.nash_cournot.solver`` — import ``pe.features.nash_cournot.solver`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.nash_cournot.solver import *  # noqa

warnings.warn(
    "ets.features.nash_cournot.solver is deprecated; import pe.features.nash_cournot.solver instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
