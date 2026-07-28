from __future__ import annotations

from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationCardsRevealed,
    PresentationOverflowResolved,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
    PresentationTrickFinished,
)
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.protocol.messages import PlayedCardView


def _player_name(
    player_id: PlayerID, player_names: dict[PlayerID, str], fallback: str = "?"
) -> str:
    return player_names.get(player_id, fallback)


def build_presentation_cards_revealed(
    plays: tuple[PlayedCardView, ...],
) -> PresentationCardsRevealed:
    return PresentationCardsRevealed(plays=plays)


def build_presentation_card_placed(
    *,
    player_id: PlayerID,
    player_names: dict[PlayerID, str],
    card_value: int,
    row_id: RowID,
    row_cards_after: tuple[int, ...],
) -> PresentationCardPlaced:
    return PresentationCardPlaced(
        player_id=player_id,
        player_name=_player_name(player_id, player_names),
        card_value=card_value,
        row_id=row_id,
        row_cards_after=row_cards_after,
    )


def build_presentation_row_choice_required(
    *,
    player_id: PlayerID,
    player_names: dict[PlayerID, str],
    card_value: int,
) -> PresentationRowChoiceRequired:
    return PresentationRowChoiceRequired(
        player_id=player_id,
        player_name=_player_name(player_id, player_names),
        card_value=card_value,
    )


def build_presentation_row_chosen(
    *,
    player_id: PlayerID,
    player_names: dict[PlayerID, str],
    row_id: RowID,
    card_value: int,
) -> PresentationRowChosen:
    return PresentationRowChosen(
        player_id=player_id,
        player_name=_player_name(player_id, player_names),
        row_id=row_id,
        card_value=card_value,
    )


def build_presentation_row_taken(
    *,
    player_id: PlayerID,
    player_names: dict[PlayerID, str],
    row_id: RowID,
    taken_cards: tuple[int, ...],
    bullheads: int,
    replacement_card_value: int,
    row_cards_after: tuple[int, ...],
) -> PresentationRowTaken:
    return PresentationRowTaken(
        player_id=player_id,
        player_name=_player_name(player_id, player_names),
        row_id=row_id,
        taken_cards=taken_cards,
        bullheads=bullheads,
        replacement_card_value=replacement_card_value,
        row_cards_after=row_cards_after,
    )


def build_presentation_overflow_resolved(
    *,
    player_id: PlayerID,
    player_names: dict[PlayerID, str],
    row_id: RowID,
    card_value: int,
    taken_cards: tuple[int, ...],
    bullheads: int,
    row_cards_after: tuple[int, ...],
) -> PresentationOverflowResolved:
    return PresentationOverflowResolved(
        player_id=player_id,
        player_name=_player_name(player_id, player_names),
        row_id=row_id,
        card_value=card_value,
        taken_cards=taken_cards,
        bullheads=bullheads,
        row_cards_after=row_cards_after,
    )


def build_presentation_trick_finished() -> PresentationTrickFinished:
    return PresentationTrickFinished()
