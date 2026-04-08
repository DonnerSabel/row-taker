from __future__ import annotations

from dataclasses import dataclass

from row_taker.cli.render import render_player_state
from row_taker.cli.row_display import build_row_display_mapping
from row_taker.cli.terminal import clear_screen
from row_taker.engine.game.player_state_ops import validate_submit_card, validate_submit_row_choice
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ClientToServerMessage,
    ServerToClientMessage,
    SubmitCard,
    SubmitRowChoice,
)


@dataclass(slots=True)
class CliClient:
    def handle_server_message(self, message: ServerToClientMessage) -> ClientToServerMessage | None:
        if isinstance(message, ChooseCardRequested):
            return self._handle_choose_card_requested(message)
        if isinstance(message, ChooseRowRequested):
            return self._handle_choose_row_requested(message)
        return None

    def _handle_choose_card_requested(self, message: ChooseCardRequested) -> SubmitCard:
        state = message.state
        while True:
            clear_screen()
            render_player_state(state)

            value = input('Wähle eine Karte (Zahl) > ').strip()
            if value.isdigit():
                card_value = int(value)
                try:
                    validate_submit_card(state, card_value)
                except ValueError:
                    pass
                else:
                    return SubmitCard(
                        player_id=state.self_player_id,
                        card_value=card_value,
                    )

            input('Ungültige Wahl. Enter...')

    def _handle_choose_row_requested(self, message: ChooseRowRequested) -> SubmitRowChoice:
        state = message.state
        mapping = build_row_display_mapping(state.public_state)

        while True:
            clear_screen()
            render_player_state(state)

            pending_card_value = state.pending_card_value()
            pending_card_label = '?' if pending_card_value is None else str(pending_card_value)
            print(f'{state.self_player_name()}: Deine Karte {pending_card_label} ist kleiner als alle Reihen.')

            max_choice = mapping.max_cli_row()
            value = input(f'Welche Reihe willst du nehmen? (1-{max_choice}) > ').strip()

            if value.isdigit():
                cli_choice = int(value)
                if 1 <= cli_choice <= max_choice:
                    state_row_index = mapping.to_state_index(cli_choice)
                    row_id = state.rows[state_row_index].row_id
                    try:
                        validate_submit_row_choice(state, row_id)
                    except ValueError:
                        pass
                    else:
                        return SubmitRowChoice(
                            player_id=state.self_player_id,
                            row_id=row_id,
                        )

            print(f'Ungültig. Bitte 1-{max_choice} eingeben.')
            input('Enter...')
