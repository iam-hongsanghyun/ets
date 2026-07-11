"""Deprecated mirror of ``pe.web.handlers`` — import ``pe.web.handlers`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.web.handlers import *  # noqa

warnings.warn(
    "ets.web.handlers is deprecated; import pe.web.handlers instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
