from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from row_taker.client.presentation_events import (
    PresentationEvent,
    PresentationGameFinished,
    PresentationOverflowResolved,
    PresentationRoundFinished,
    PresentationTrickFinished,
)
from row_taker.client.state import ClientState
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.gui.game_visual_state import VisualPresentationPanel
from row_taker.gui_common.ui.common_render import format_presentation_event

RowEmphasis = Literal["none", "selectable", "placed", "choice", "taken", "overflow"]


@dataclass(frozen=True, slots=True)
class PresentationVisuals:
    """Small view model for drawing the currently active presentation step.

    The engine and client-core still own all game semantics. This module only
    translates the front-most presentation event into visual hints for pygame.
    """

    current_event: PresentationEvent | None = None
    active_row_id: RowID | None = None
    active_player_id: PlayerID | None = None
    played_card_values_by_player: dict[PlayerID, int] | None = None
    focus_card_values: tuple[int, ...] = ()
    taken_card_values: tuple[int, ...] = ()
    replacement_card_value: int | None = None
    row_emphasis: RowEmphasis = "none"
    headline: str = ""
    details: tuple[str, ...] = ()

    @property
    def has_event(self) -> bool:
        return self.current_event is not None

    def card_value_for_player(self, player_id: PlayerID) -> int | None:
        if self.played_card_values_by_player is None:
            return None
        return self.played_card_values_by_player.get(player_id)

    def row_emphasis_for(self, row_id: RowID) -> RowEmphasis:
        if self.active_row_id is None or row_id != self.active_row_id:
            return "none"
        return self.row_emphasis

    @property
    def panel(self) -> VisualPresentationPanel | None:
        if not self.has_event:
            return None
        return VisualPresentationPanel(
            headline=self.headline,
            details=self.details,
            card_values=self.focus_card_values,
        )


def build_presentation_visuals(state: ClientState) -> PresentationVisuals:
    if not state.pending_presentation_events:
        return PresentationVisuals()

    event = state.pending_presentation_events[0]
    details = tuple(format_presentation_event(item) for item in state.pending_presentation_events[:3])

    if isinstance(event, PresentationOverflowResolved):
        return PresentationVisuals(
            current_event=event,
            active_row_id=event.row_id,
            active_player_id=event.player_id,
            played_card_values_by_player={event.player_id: event.card_value},
            focus_card_values=(event.card_value,),
            taken_card_values=event.taken_cards,
            row_emphasis="overflow",
            headline=f"Overflow: {event.player_name} nimmt Reihe {event.row_id}",
            details=details,
        )

    if isinstance(event, PresentationTrickFinished):
        return PresentationVisuals(current_event=event, headline="Stich beendet", details=details)

    if isinstance(event, PresentationRoundFinished):
        return PresentationVisuals(current_event=event, headline="Runde beendet", details=details)

    if isinstance(event, PresentationGameFinished):
        return PresentationVisuals(current_event=event, headline="Spiel beendet", details=details)

    # Presentation types already migrated into GameVisualState deliberately
    # leave this compatibility layer empty.
    return PresentationVisuals()
