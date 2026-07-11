"""Deprecated mirror of ``pe.config_io.templates`` — import ``pe.config_io.templates`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.config_io.templates import *  # noqa

warnings.warn(
    "ets.config_io.templates is deprecated; import pe.config_io.templates instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
