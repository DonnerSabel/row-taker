from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.phases import StepAction
from row_taker.engine.game.public_state_ops import (
    apply_delta_public_state,
    classify_public_delta,
    played_card_from_delta,
    score_delta_for_public_delta,
)
from row_taker.engine.game.state import DeltaPublicState, PublicState


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


def format_public_deltas_for_cli(before_state: PublicState, deltas: list[DeltaPublicState] | tuple[DeltaPublicState, ...]) -> list[str]:
    shadow_state = before_state
    lines: list[str] = []

    for delta in deltas:
        row_index = shadow_state.get_row_index(delta.affected_row_id)
        mapping = build_row_display_mapping(shadow_state)
        cli_row = mapping.to_cli_row(row_index)
        player = next(player for player in shadow_state.players if player.player_id == delta.player_id)
        transition_kind = classify_public_delta(shadow_state, delta)
        bullheads = score_delta_for_public_delta(shadow_state, delta)
        played_card = played_card_from_delta(delta)

        if transition_kind == StepAction.PLACED:
            lines.append(f'- {player.name} legt {played_card.value} an Reihe {cli_row}.')
        elif transition_kind == StepAction.TOOK_ROW_SMALL:
            lines.append(
                f'- {player.name} nimmt Reihe {cli_row} ({bullheads} Hornochsen) '
                f'und startet mit {played_card.value}.'
            )
        elif transition_kind == StepAction.TOOK_ROW_OVERFLOW:
            lines.append(
                f'- {player.name} füllt Reihe {cli_row} (nimmt {bullheads} Hornochsen) '
                f'und startet mit {played_card.value}.'
            )
        else:
            raise ValueError(f'Unbekannte Delta-Klassifikation: {transition_kind}')

        shadow_state = apply_delta_public_state(shadow_state, delta)

    return lines
