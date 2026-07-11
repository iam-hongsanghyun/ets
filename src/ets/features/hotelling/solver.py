"""Deprecated mirror of ``pe.features.hotelling.solver`` — import ``pe.features.hotelling.solver`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.hotelling.solver import *  # noqa

warnings.warn(
    "ets.features.hotelling.solver is deprecated; import pe.features.hotelling.solver instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
