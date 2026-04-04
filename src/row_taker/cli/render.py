from __future__ import annotations

from row_taker.cli.row_display import build_row_display_mapping, format_results_for_cli
from row_taker.engine.state import PlayerState, PublicState
from row_taker.hub.match_hub import TrickResult


def render_public_state(state: PublicState) -> None:
    print(f'Runde: {state.round_no}')
    print(f'Stich: {state.trick_no}')
    print()
    print('Reihen:')

    mapping = build_row_display_mapping(state)

    for cli_row, state_row_index in enumerate(mapping.row_order, start=1):
        row = state.rows[state_row_index]
        vals = ' '.join(f'{c.value:>3}' for c in row.cards)
        bullheads = row.bullheads()
        print(f'  Reihe {cli_row}: {vals:<25}  ({bullheads} Hornochsen)')

    print()
    print('Scores:')
    for i, p in enumerate(state.players):
        print(f'  ({i}) {p.name}: {p.score}')
    print()


def render_handcards(state: PlayerState) -> None:
    own_name = next(
        player.name for player in state.players if player.player_id == state.self_player_id
    )
    print(f'{own_name}: Deine Handkarten:')
    print('  ' + ' '.join(f'|{card.value} {card.bullheads * "🐮"}|' for card in state.hand))


def render_player_state(state: PlayerState) -> None:
    render_public_state(state.public_state)

    print('Scores mit Handkarten:')
    for i, p in enumerate(state.players):
        you = ' <- du' if p.player_id == state.self_player_id else ''
        print(f'  ({i}) {p.name}: {p.score}, {p.hand_count} Karten{you}')
    print()

    render_handcards(state)


def render_trick_result(result: TrickResult) -> None:
    result_lines = format_results_for_cli(result.public_state_before, result.resolution)
    render_public_state(result.public_state_after)

    print('Auflösung:')
    for line in result_lines:
        print(line)

    if result.new_round_started:
        print()
        print('== Neue Runde wurde ausgeteilt. ==')
