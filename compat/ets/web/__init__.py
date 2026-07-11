"""Deprecated mirror of ``pe.web`` — import ``pe.web`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.web import *  # noqa

warnings.warn(
    "ets.web is deprecated; import pe.web instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
