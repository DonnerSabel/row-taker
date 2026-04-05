from __future__ import annotations

import random

from row_taker.cli.create_match_config import create_match_config
from row_taker.cli.render import render_public_state, render_trick_result
from row_taker.cli.terminal import clear_screen
from row_taker.engine.game import setup_game
from row_taker.hub.match_config import ParticipantKind
from row_taker.hub.match_hub import MatchHub
from row_taker.hub.messages import ChooseCardRequested, ChooseRowRequested, TrickResolved
from row_taker.participants.cli_participant import CliParticipant
from row_taker.participants.client import Client
from row_taker.participants.random_bot_participant import RandomBotParticipant


def main() -> None:
    rng = random.Random()

    clear_screen()
    print('Row-Taker – CLI (Hotseat)')
    print()

    match_config = create_match_config()
    player_names = [seat.name for seat in match_config.seats]
    state = setup_game(player_names, rng=rng)

    clients_by_player_id: dict[object, Client] = {}
    for seat, player in zip(match_config.seats, state.players, strict=True):
        if seat.kind == ParticipantKind.HUMAN:
            clients_by_player_id[player.player_id] = CliParticipant()
        elif seat.kind == ParticipantKind.RANDOM_BOT:
            clients_by_player_id[player.player_id] = RandomBotParticipant(rng=rng)
        else:
            raise ValueError(f'unsupported participant kind: {seat.kind!r}')

    hub = MatchHub(state=state)

    while True:
        hub.start_trick()
        trick_result = _run_trick_until_resolved(hub, clients_by_player_id)

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
    render_public_state(hub.build_public_state())
    winner = min(hub.state.players, key=lambda p: p.score)
    print(f'Gewonnen hat: {winner.name} (wenigste Hornochsen)')


def _run_trick_until_resolved(
    hub: MatchHub,
    clients_by_player_id: dict[object, Client],
) -> TrickResolved:
    while True:
        messages = hub.drain_outbox()
        if not messages:
            raise ValueError('hub outbox unexpectedly empty before trick was resolved')

        for message in messages:
            if isinstance(message, TrickResolved):
                return message

            if isinstance(message, (ChooseCardRequested, ChooseRowRequested)):
                client = clients_by_player_id[message.player_id]
                for client_message in client.handle_hub_message(message):
                    hub.handle_client_message(client_message)


def run() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        clear_screen()
        print('Abbruch mit Strg+C!')
        return 0
