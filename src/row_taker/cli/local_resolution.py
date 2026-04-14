from __future__ import annotations

from row_taker.client.trick_presentation_resolver import (
    TrickPresentationState as LocalResolutionState,
)
from row_taker.client.trick_presentation_resolver import (
    apply_trick_row_choice as apply_local_row_choice,
)
from row_taker.client.trick_presentation_resolver import (
    start_trick_presentation as start_local_resolution,
)

__all__ = [
    "LocalResolutionState",
    "apply_local_row_choice",
    "start_local_resolution",
]
