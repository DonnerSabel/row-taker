from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.phases import StepAction
from row_taker.engine.game.public_state_ops import apply_resolution_step
from row_taker.engine.game.state import PublicState, TrickResolutionStep


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


def format_resolution_steps_for_cli(
    before_state: PublicState, steps: list[TrickResolutionStep] | tuple[TrickResolutionStep, ...]
) -> list[str]:
    shadow_state = before_state
    lines: list[str] = []

    for step in steps:
        row_index = shadow_state.get_row_index(step.affected_row_id)
        mapping = build_row_display_mapping(shadow_state)
        cli_row = mapping.to_cli_row(row_index)
        player = next(
            player for player in shadow_state.players if player.player_id == step.player_id
        )

        if step.action == StepAction.PLACED:
            lines.append(f"- {player.name} legt {step.played_card.value} an Reihe {cli_row}.")
        elif step.action == StepAction.TOOK_ROW_SMALL:
            lines.append(
                f"- {player.name} nimmt Reihe {cli_row} ({step.points_gained} Hornochsen) "
                f"und startet mit {step.played_card.value}."
            )
        elif step.action == StepAction.TOOK_ROW_OVERFLOW:
            lines.append(
                f"- {player.name} füllt Reihe {cli_row} (nimmt {step.points_gained} Hornochsen) "
                f"und startet mit {step.played_card.value}."
            )
        else:
            raise ValueError(f"Unbekannte Schritt-Klassifikation: {step.action}")

        shadow_state = apply_resolution_step(shadow_state, step)

    return lines
