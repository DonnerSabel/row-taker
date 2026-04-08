from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import Card, PlayerID, RowID


class Phase(StrEnum):
    ROUND_SETUP = "round_setup"
    CHOOSE_CARD = "choose_card"
    REVEAL_AND_RESOLVE = "reveal_and_resolve"
    CHOOSE_ROW = "choose_row"
    ROUND_SCORING = "round_scoring"
    GAME_OVER = "game_over"


class StepAction(StrEnum):
    PLACED = "placed"
    TOOK_ROW_SMALL = "took_row_small"
    TOOK_ROW_OVERFLOW = "took_row_overflow"


@dataclass(frozen=True, slots=True)
class PhaseInfo:
    phase: Phase

    # Falls genau ein Spieler jetzt entscheiden muss:
    active_player_id: PlayerID | None = None

    # Relevant bei choose_row:
    pending_card: Card | None = None
    selectable_row_ids: tuple[RowID, ...] = ()

    # Optional für Client/Anzeige:
    message: str = ""
