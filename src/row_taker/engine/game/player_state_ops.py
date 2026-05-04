from __future__ import annotations

from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import RowID
from row_taker.engine.game.state import PlayerState


def validate_submit_card(player_state: PlayerState, card_value: int) -> None:
    player_state.validate_card_value(card_value)


def validate_submit_row_choice(player_state: PlayerState, row_id: RowID) -> None:
    player_state.validate_selectable_row_id(row_id)


def selectable_row_ids(player_state: PlayerState) -> tuple[RowID, ...]:
    return player_state.get_selectable_row_ids_for_choose_row()


def playable_cards(player_state: PlayerState) -> tuple[Card, ...]:
    return tuple(player_state.hand)


def playable_card_values(player_state: PlayerState) -> tuple[int, ...]:
    return player_state.playable_card_values()
