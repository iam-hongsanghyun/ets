"""Deprecated mirror of ``pe.core.ledger`` — import ``pe.core.ledger`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.core.ledger import *  # noqa

warnings.warn(
    "ets.core.ledger is deprecated; import pe.core.ledger instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
