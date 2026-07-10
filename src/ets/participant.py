# Backward-compatibility shim — re-exports from the participant sub-package.
# New location: src/ets/participant/ (the sub-package).
# Note: Python resolves 'participant' to the participant/ package when both
# exist, so this module is shadowed and never imported; the warning below is
# kept for the removal milestone bookkeeping.
import warnings

from .participant import MarketParticipant, TechnologyOption, ComplianceOutcome, CostSpec

warnings.warn(
    "the flat ets/participant.py shim is deprecated; import from the "
    "ets.participant sub-package instead. "
    "Removal milestone: after the frontend migrates to the graph API (v2.0).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "MarketParticipant",
    "TechnologyOption",
    "ComplianceOutcome",
    "CostSpec",
]
