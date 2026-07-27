from __future__ import annotations

from dataclasses import dataclass

from row_taker.client.presentation_events import PresentationEvent
from row_taker.engine.game.state import PublicState


@dataclass(frozen=True, slots=True)
class PresentationStep:
    """One presentation event with its logical before/after snapshots."""

    event: PresentationEvent
    public_state_before: PublicState
    public_state_after: PublicState
