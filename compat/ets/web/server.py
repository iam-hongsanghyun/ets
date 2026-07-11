"""Deprecated mirror of ``pe.web.server`` — import ``pe.web.server`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.web.server import *  # noqa

warnings.warn(
    "ets.web.server is deprecated; import pe.web.server instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
