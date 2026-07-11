"""Deprecated mirror of ``pe.cli`` — import ``pe.cli`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.cli import *  # noqa

warnings.warn(
    "ets.cli is deprecated; import pe.cli instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
