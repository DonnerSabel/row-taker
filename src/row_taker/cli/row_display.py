from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from row_taker.engine.game import StepResult
from row_taker.engine.models import PublicPlayerInfo
from row_taker.engine.phases import StepAction
from row_taker.engine.state import PublicState, get_player_index, get_row_index


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


def build_row_display_mapping(state: PublicState) -> RowDisplayMapping:
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


def _replace_public_player_score(
    state: PublicState,
    player_index: int,
    bullheads_delta: int,
) -> None:
    old_player = state.players[player_index]
    state.players[player_index] = PublicPlayerInfo(
        player_id=old_player.player_id,
        name=old_player.name,
        score=old_player.score + bullheads_delta,
        hand_count=old_player.hand_count,
    )


def apply_result_to_shadow_state(state: PublicState, result: StepResult) -> None:
    row_index = get_row_index(state.rows, result.row_id)
    player_index = get_player_index(state.players, result.player_id)
    row = state.rows[row_index]

    if result.action == StepAction.PLACED:
        row.cards.append(result.card)
        return

    if result.action in {StepAction.TOOK_ROW_SMALL, StepAction.TOOK_ROW_OVERFLOW}:
        row.cards = [result.card]
        _replace_public_player_score(state, player_index, result.bullheads_gained)
        return

    raise ValueError(f"Unbekannte Aktion: {result.action}")


def format_results_for_cli(before_state: PublicState, results: list[StepResult]) -> list[str]:
    shadow_state = deepcopy(before_state)
    lines: list[str] = []

    for result in results:
        row_index = get_row_index(shadow_state.rows, result.row_id)
        player_index = get_player_index(shadow_state.players, result.player_id)

        mapping = build_row_display_mapping(shadow_state)
        cli_row = mapping.to_cli_row(row_index)
        player = shadow_state.players[player_index]

        if result.action == StepAction.PLACED:
            lines.append(f"- {player.name} legt {result.card.value} an Reihe {cli_row}.")
        elif result.action == StepAction.TOOK_ROW_SMALL:
            lines.append(
                f"- {player.name} nimmt Reihe {cli_row} ({result.bullheads_gained} Hornochsen) "
                f"und startet mit {result.card.value}."
            )
        elif result.action == StepAction.TOOK_ROW_OVERFLOW:
            lines.append(
                f"- {player.name} füllt Reihe {cli_row} (nimmt {result.bullheads_gained} Hornochsen) "
                f"und startet mit {result.card.value}."
            )
        else:
            raise ValueError(f"Unbekannte Aktion: {result.action}")

        apply_result_to_shadow_state(shadow_state, result)

    return lines
