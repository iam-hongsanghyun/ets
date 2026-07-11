"""Deprecated mirror of ``pe.web.api`` — import ``pe.web.api`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.web.api import *  # noqa

warnings.warn(
    "ets.web.api is deprecated; import pe.web.api instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
