"""Deprecated mirror of ``pe.features.elastic_baseline`` — import ``pe.features.elastic_baseline`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.elastic_baseline import *  # noqa

warnings.warn(
    "ets.features.elastic_baseline is deprecated; import pe.features.elastic_baseline instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
