# Backward-compatibility shim — re-exports from core.participant.models.
# New location: src/ets/core/participant/models.py.
import warnings

from pe.core.participant.models import (
    CostSpec,
    TechnologyOption,
    ComplianceOutcome,
    MarketParticipant,
)

warnings.warn(
    "ets.participant.models is deprecated; import from "
    "pe.core.participant.models instead. Removal milestone: 0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "CostSpec",
    "TechnologyOption",
    "ComplianceOutcome",
    "MarketParticipant",
]
