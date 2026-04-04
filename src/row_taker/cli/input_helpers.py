from __future__ import annotations

import os
import sys

from row_taker.cli.render import render_player_state
from row_taker.cli.row_display import build_row_display_mapping
from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.state import PlayerState


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if os.name != 'nt' and not os.environ.get('TERM'):
        return
    os.system('cls' if os.name == 'nt' else 'clear')


def choose_card_cli(state: PlayerState) -> PlayCardCommand:
    while True:
        clear_screen()
        render_player_state(state)

        own_name = next(
            p.name for p in state.players if p.player_id == state.self_player_id
        )
        print(f'{own_name}: Deine Handkarten:')
        print('  ' + ' '.join(f'|{c.value} {c.points * "🐮"}|' for c in state.hand))

        s = input('Wähle eine Karte (Zahl) > ').strip()
        if s.isdigit():
            v = int(s)
            for c in state.hand:
                if c.value == v:
                    return PlayCardCommand(
                        player_id=state.self_player_id,
                        card_value=c.value,
                    )

        input('Ungültige Wahl. Enter...')


def choose_row_cli_from_player_state(state: PlayerState) -> ChooseRowCommand:
    mapping = build_row_display_mapping(state)

    while True:
        clear_screen()
        render_player_state(state)

        own_name = next(
            p.name for p in state.players if p.player_id == state.self_player_id
        )
        pending_card_value = (
            state.phase_info.pending_card.value
            if state.phase_info.pending_card is not None
            else '?'
        )
        print(
            f'{own_name}: Deine Karte {pending_card_value} ist kleiner als alle Reihen.'
        )

        allowed_row_ids = set(state.phase_info.selectable_row_ids)
        max_choice = mapping.max_cli_row()
        s = input(f'Welche Reihe willst du nehmen? (1-{max_choice}) > ').strip()

        if s.isdigit():
            cli_choice = int(s)
            if 1 <= cli_choice <= max_choice:
                state_row_index = mapping.to_state_index(cli_choice)
                row_id = state.rows[state_row_index].row_id
                if row_id in allowed_row_ids:
                    return ChooseRowCommand(
                        player_id=state.self_player_id,
                        row_id=row_id,
                    )

        print(f'Ungültig. Bitte 1-{max_choice} eingeben.')
        input('Enter...')
