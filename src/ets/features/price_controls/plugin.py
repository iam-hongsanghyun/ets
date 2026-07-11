"""Deprecated mirror of ``pe.features.price_controls.plugin`` — import ``pe.features.price_controls.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.price_controls.plugin import *  # noqa

warnings.warn(
    "ets.features.price_controls.plugin is deprecated; import pe.features.price_controls.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
