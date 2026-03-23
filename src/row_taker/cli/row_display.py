from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from row_taker.engine.game import StepResult
from row_taker.engine.models import PublicPlayerInfo
from row_taker.engine.state import PlayerState


@dataclass(slots=True, frozen=True)
class RowDisplayMapping:
    row_order: list[int]
    cli_to_state: dict[int, int]
    state_to_cli: dict[int, int]

    def max_cli_row(self) -> int:
        return len(self.row_order)

    def to_state_index(self, cli_row: int) -> int:
        return self.cli_to_state[cli_row]

    def to_cli_row(self, state_row_index: int) -> int:
        return self.state_to_cli[state_row_index]


def build_row_display_mapping(state: PlayerState) -> RowDisplayMapping:
    row_order = sorted(
        range(len(state.rows)),
        key=lambda row_index: (
            state.rows[row_index].cards[-1].value if state.rows[row_index].cards else 0
        ),
    )

    cli_to_state = {
        cli_row: state_index
        for cli_row, state_index in enumerate(row_order, start=1)
    }
    state_to_cli = {
        state_index: cli_row
        for cli_row, state_index in cli_to_state.items()
    }

    return RowDisplayMapping(
        row_order=row_order,
        cli_to_state=cli_to_state,
        state_to_cli=state_to_cli,
    )


def _find_row_index_by_id(state: PlayerState, row_id: str) -> int:
    for index, row in enumerate(state.rows):
        if row.row_id == row_id:
            return index
    raise ValueError(f"unknown row_id: {row_id!r}")


def _find_player_index_by_id(state: PlayerState, player_id: str) -> int:
    for index, player in enumerate(state.players):
        if player.player_id == player_id:
            return index
    raise ValueError(f"unknown player_id: {player_id!r}")


def _replace_public_player_score(
    state: PlayerState,
    player_index: int,
    points_delta: int,
) -> None:
    old_player = state.players[player_index]
    state.players[player_index] = PublicPlayerInfo(
        player_id=old_player.player_id,
        name=old_player.name,
        score=old_player.score + points_delta,
        hand_count=old_player.hand_count,
    )


def apply_result_to_shadow_state(state: PlayerState, result: StepResult) -> None:
    row_index = _find_row_index_by_id(state, result.row_id)
    player_index = _find_player_index_by_id(state, result.player_id)
    row = state.rows[row_index]

    if result.action == "placed":
        row.cards.append(result.card)
        return

    if result.action in {"took_row_small", "took_row_overflow"}:
        row.cards = [result.card]
        _replace_public_player_score(state, player_index, result.points_gained)
        return

    raise ValueError(f"Unbekannte Aktion: {result.action}")


def format_results_for_cli(before_state: PlayerState, results: list[StepResult]) -> list[str]:
    shadow_state = deepcopy(before_state)
    lines: list[str] = []

    for result in results:
        row_index = _find_row_index_by_id(shadow_state, result.row_id)
        player_index = _find_player_index_by_id(shadow_state, result.player_id)

        mapping = build_row_display_mapping(shadow_state)
        cli_row = mapping.to_cli_row(row_index)
        player = shadow_state.players[player_index]

        if result.action == "placed":
            lines.append(f"- {player.name} legt {result.card.value} an Reihe {cli_row}.")
        elif result.action == "took_row_small":
            lines.append(
                f"- {player.name} nimmt Reihe {cli_row} ({result.points_gained} Punkte) "
                f"und startet mit {result.card.value}."
            )
        elif result.action == "took_row_overflow":
            lines.append(
                f"- {player.name} füllt Reihe {cli_row} (nimmt {result.points_gained} Punkte) "
                f"und startet mit {result.card.value}."
            )
        else:
            raise ValueError(f"Unbekannte Aktion: {result.action}")

        apply_result_to_shadow_state(shadow_state, result)

    return lines
