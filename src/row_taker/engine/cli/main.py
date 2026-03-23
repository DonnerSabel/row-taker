from __future__ import annotations

from dataclasses import dataclass

from ..commands import ChooseRowCommand, PlayCardCommand
from ..models import Card, RowID
from ..phases import Phase
from ..state import PlayerState


@dataclass(frozen=True, slots=True)
class RowNumberMapping:
    number_to_row_id: dict[int, RowID]


def build_row_number_mapping(state: PlayerState) -> RowNumberMapping:
    return RowNumberMapping(
        number_to_row_id={
            index: row.row_id
            for index, row in enumerate(state.rows, start=1)
        }
    )


def render_player_state(state: PlayerState) -> str:
    lines: list[str] = []
    lines.append(f"Round {state.round_no}, trick {state.trick_no}")
    lines.append(f"Phase: {state.phase_info.phase}")

    if state.phase_info.message:
        lines.append(state.phase_info.message)

    lines.append("")
    lines.append("Players:")
    for player in state.players:
        marker = " <- you" if player.player_id == state.self_player_id else ""
        lines.append(
            f"  {player.name}: {player.score} points, {player.hand_count} cards{marker}"
        )

    lines.append("")
    lines.append("Rows:")
    for index, row in enumerate(state.rows, start=1):
        values = " ".join(str(card.value) for card in row.cards)
        lines.append(
            f"  {index}: [{values}]  last={row.last_value()}  points={row.points()}"
        )

    lines.append("")
    hand_values = " ".join(str(card.value) for card in state.hand)
    lines.append(f"Your hand: {hand_values}")

    if state.phase_info.phase == Phase.CHOOSE_ROW:
        selectable = ", ".join(state.phase_info.selectable_row_ids)
        lines.append(f"Selectable row ids: {selectable}")

    return "\n".join(lines)


def _find_card_by_value(hand: list[Card], card_value: int) -> Card | None:
    for card in hand:
        if card.value == card_value:
            return card
    return None


def choose_card_cli(state: PlayerState) -> PlayCardCommand:
    if state.phase_info.phase != Phase.CHOOSE_CARD:
        raise ValueError(
            f"choose_card_cli called outside choose_card phase: {state.phase_info.phase!r}"
        )

    print(render_player_state(state))
    while True:
        raw = input("Choose card value: ").strip()
        try:
            card_value = int(raw)
        except ValueError:
            print("Please enter a valid integer card value.")
            continue

        card = _find_card_by_value(state.hand, card_value)
        if card is None:
            print("You do not have that card.")
            continue

        return PlayCardCommand(
            player_id=state.self_player_id,
            card_value=card.value,
        )


def choose_row_cli(state: PlayerState) -> ChooseRowCommand:
    if state.phase_info.phase != Phase.CHOOSE_ROW:
        raise ValueError(
            f"choose_row_cli called outside choose_row phase: {state.phase_info.phase!r}"
        )

    mapping = build_row_number_mapping(state)
    allowed_row_ids = set(state.phase_info.selectable_row_ids)

    print(render_player_state(state))
    while True:
        raw = input("Choose row number to take: ").strip()
        try:
            row_number = int(raw)
        except ValueError:
            print("Please enter a valid row number.")
            continue

        row_id = mapping.number_to_row_id.get(row_number)
        if row_id is None:
            print("That row number does not exist.")
            continue

        if row_id not in allowed_row_ids:
            print("That row is currently not selectable.")
            continue

        return ChooseRowCommand(
            player_id=state.self_player_id,
            row_id=row_id,
        )


def main() -> int:
    print(
        "This module provides CLI helper functions for PlayerState-based clients.\n"
        "Use choose_card_cli(...) and choose_row_cli(...) from a local runner or hub adapter."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
