"""Deprecated mirror of ``pe.features.competitive.solver`` — import ``pe.features.competitive.solver`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.competitive.solver import *  # noqa

warnings.warn(
    "ets.features.competitive.solver is deprecated; import pe.features.competitive.solver instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
