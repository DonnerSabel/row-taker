from copy import deepcopy
from dataclasses import dataclass

from row_taker.engine.game import StepResult
from row_taker.engine.state import GameState


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


def build_row_display_mapping(state: GameState) -> RowDisplayMapping:
    row_order = sorted(
        range(len(state.rows)),
        key=lambda row_index: state.rows[row_index].cards[-1].value if state.rows[row_index].cards else 0,
    )

    cli_to_state = {cli_row: state_index for cli_row, state_index in enumerate(row_order, start=1)}
    state_to_cli = {state_index: cli_row for cli_row, state_index in cli_to_state.items()}

    return RowDisplayMapping(
        row_order=row_order,
        cli_to_state=cli_to_state,
        state_to_cli=state_to_cli,
    )


def apply_result_to_shadow_state(state: GameState, result: StepResult) -> None:
    row = state.rows[result.row_index]

    if result.action == "placed":
        row.cards.append(result.card)
        return

    if result.action in {"took_row_small", "took_row_overflow"}:
        row.cards = [result.card]
        state.players[result.player_index].score += result.points_gained
        return

    raise ValueError(f"Unbekannte Aktion: {result.action}")


def format_results_for_cli(before_state: GameState, results: list[StepResult]) -> list[str]:
    shadow_state = deepcopy(before_state)
    lines: list[str] = []

    for result in results:
        mapping = build_row_display_mapping(shadow_state)
        cli_row = mapping.to_cli_row(result.row_index)
        player = shadow_state.players[result.player_index]

        if result.action == "placed":
            lines.append(f"- {player.name} legt {result.card.value} an Reihe {cli_row}.")
        elif result.action == "took_row_small":
            lines.append(
                f"- {player.name} nimmt Reihe {cli_row} ({result.points_gained} Punkte) und startet mit {result.card.value}."
            )
        elif result.action == "took_row_overflow":
            lines.append(
                f"- {player.name} füllt Reihe {cli_row} (nimmt {result.points_gained} Punkte) und startet mit {result.card.value}."
            )
        else:
            raise ValueError(f"Unbekannte Aktion: {result.action}")

        apply_result_to_shadow_state(shadow_state, result)

    return lines
