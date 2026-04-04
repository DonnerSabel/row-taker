from __future__ import annotations

import os
import random
import sys

from row_taker.cli.create_match_config import create_match_config
from row_taker.cli.render import render_public_state, render_trick_result
from row_taker.engine.game import setup_game
from row_taker.hub.match_config import ParticipantKind
from row_taker.hub.match_hub import MatchHub
from row_taker.participants.cli_participant import CliParticipant
from row_taker.participants.random_bot_participant import RandomBotParticipant


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if os.name != 'nt' and not os.environ.get('TERM'):
        return
    os.system('cls' if os.name == 'nt' else 'clear')


def main() -> None:
    rng = random.Random()

    clear_screen()
    print('Row-Taker – CLI (Hotseat)')
    print()

    match_config = create_match_config()
    player_names = [seat.name for seat in match_config.seats]
    state = setup_game(player_names, rng=rng)

    participants_by_player_id = {}
    for seat, player in zip(match_config.seats, state.players, strict=True):
        if seat.kind == ParticipantKind.HUMAN:
            participants_by_player_id[player.player_id] = CliParticipant()
        elif seat.kind == ParticipantKind.RANDOM_BOT:
            participants_by_player_id[player.player_id] = RandomBotParticipant(rng=rng)
        else:
            raise ValueError(f'unsupported participant kind: {seat.kind!r}')

    hub = MatchHub(
        state=state,
        participants_by_player_id=participants_by_player_id,
    )

    while True:
        trick_result = hub.play_trick()

        clear_screen()
        render_trick_result(trick_result)

        if trick_result.game_finished:
            break

        print()
        cont = input("Enter für nächsten Stich, 'q' zum Beenden > ").strip().lower()
        if cont == 'q':
            break

    print()
    print('Endstand:')
    render_public_state(hub.build_public_player_state())
    winner = min(hub.state.players, key=lambda p: p.score)
    print(f'Gewonnen hat: {winner.name} (wenigste Hornochsen)')


def run() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        clear_screen()
        print('Abbruch mit Strg+C!')
        return 0
