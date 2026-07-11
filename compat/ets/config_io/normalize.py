"""Deprecated mirror of ``pe.config_io.normalize`` — import ``pe.config_io.normalize`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.config_io.normalize import *  # noqa

warnings.warn(
    "ets.config_io.normalize is deprecated; import pe.config_io.normalize instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
