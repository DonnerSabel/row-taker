from __future__ import annotations

from dataclasses import dataclass

from .models import Card, PlayerID, RowID


class Phase:
    ROUND_SETUP = "round_setup"
    CHOOSE_CARD = "choose_card"
    REVEAL_AND_RESOLVE = "reveal_and_resolve"
    CHOOSE_ROW = "choose_row"
    ROUND_SCORING = "round_scoring"
    GAME_OVER = "game_over"


@dataclass(frozen=True, slots=True)
class PhaseInfo:
    phase: str

    # Falls genau ein Spieler jetzt entscheiden muss:
    active_player_id: PlayerID | None = None

    # Relevant bei choose_row:
    pending_card: Card | None = None
    selectable_row_ids: tuple[RowID, ...] = ()

    # Optional für Client/Anzeige:
    message: str = ""
