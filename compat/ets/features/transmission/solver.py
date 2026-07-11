"""Deprecated mirror of ``pe.features.transmission.solver`` — import ``pe.features.transmission.solver`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.transmission.solver import *  # noqa

warnings.warn(
    "ets.features.transmission.solver is deprecated; import pe.features.transmission.solver instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
