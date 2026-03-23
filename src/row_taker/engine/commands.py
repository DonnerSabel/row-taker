from dataclasses import dataclass

from .models import PlayerID, RowID


@dataclass(frozen=True, slots=True)
class PlayCardCommand:
    player_id: PlayerID
    card_value: int


@dataclass(frozen=True, slots=True)
class ChooseRowCommand:
    player_id: PlayerID
    row_id: RowID
