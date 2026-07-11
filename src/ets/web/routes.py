"""Deprecated mirror of ``pe.web.routes`` — import ``pe.web.routes`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.web.routes import *  # noqa

warnings.warn(
    "ets.web.routes is deprecated; import pe.web.routes instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
