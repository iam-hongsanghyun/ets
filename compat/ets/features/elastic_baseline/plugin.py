"""Deprecated mirror of ``pe.features.elastic_baseline.plugin`` — import ``pe.features.elastic_baseline.plugin`` instead.

Kept for the ets->pe rename window (D0-R1); removed at 0.4.0.
"""

import warnings

from pe.features.elastic_baseline.plugin import *  # noqa

warnings.warn(
    "ets.features.elastic_baseline.plugin is deprecated; import pe.features.elastic_baseline.plugin instead. "
    "Removal milestone: 0.4.0.",
    DeprecationWarning,
    stacklevel=2,
)
