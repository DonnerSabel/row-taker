from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.state import PublicState


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

    cli_to_state = {cli_row: state_index for cli_row, state_index in enumerate(row_order, start=1)}
    state_to_cli = {state_index: cli_row for cli_row, state_index in cli_to_state.items()}

    return RowDisplayMapping(
        row_order=row_order,
        cli_to_state=cli_to_state,
        state_to_cli=state_to_cli,
    )
