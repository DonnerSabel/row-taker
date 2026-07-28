from __future__ import annotations

from row_taker.client.presentation_events import PresentationCardPlaced
from row_taker.client.presentation_text import format_presentation_event
from row_taker.engine.game.models import PlayerID, RowID


def test_card_placed_has_human_readable_presentation_text() -> None:
    event = PresentationCardPlaced(
        player_id=PlayerID("player-ada"),
        player_name="Ada",
        card_value=44,
        row_id=RowID("row-1"),
        row_cards_after=(25, 31, 36, 44),
    )

    assert format_presentation_event(event) == "Karte angelegt -> Ada legt 44 an Reihe row-1"
