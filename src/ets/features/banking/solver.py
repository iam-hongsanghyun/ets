"""Deprecated mirror of ``pe.features.banking.solver`` — import ``pe.features.banking.solver`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.banking.solver import *  # noqa

warnings.warn(
    "ets.features.banking.solver is deprecated; import pe.features.banking.solver instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
