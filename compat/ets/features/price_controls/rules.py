"""Deprecated mirror of ``pe.features.price_controls.rules`` — import ``pe.features.price_controls.rules`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.price_controls.rules import *  # noqa

warnings.warn(
    "ets.features.price_controls.rules is deprecated; import pe.features.price_controls.rules instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
