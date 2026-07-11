"""Deprecated mirror of ``pe.analysis.investment_trigger`` — import ``pe.analysis.investment_trigger`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.analysis.investment_trigger import *  # noqa

warnings.warn(
    "ets.analysis.investment_trigger is deprecated; import pe.analysis.investment_trigger instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
