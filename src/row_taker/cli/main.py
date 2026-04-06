from __future__ import annotations

import random

from row_taker.cli.create_match_config import create_match_config
from row_taker.cli.render import render_public_state
from row_taker.cli.terminal import clear_screen
from row_taker.clients.cli_client import CliClient
from row_taker.clients.random_bot_client import RandomBotClient
from row_taker.hub.match_config import ClientKind
from row_taker.protocol.messages import ConfigureLobby, StartGame
from row_taker.server.local_server import LocalServer
from row_taker.server.local_session import run_local_session


def main() -> None:
    rng = random.Random()

    clear_screen()
    print('Row-Taker – CLI (Hotseat)')
    print()

    match_config = create_match_config()
    server = LocalServer(rng=rng)
    server.handle_client_message(ConfigureLobby(match_config=match_config))

    clients_by_player_id = {}
    for seat_index, seat in enumerate(match_config.seats):
        player_id = f'player-{seat_index}'
        if seat.kind == ClientKind.HUMAN:
            clients_by_player_id[player_id] = CliClient()
        elif seat.kind == ClientKind.RANDOM_BOT:
            clients_by_player_id[player_id] = RandomBotClient(rng=rng)
        else:
            raise ValueError(f'unsupported client kind: {seat.kind!r}')

    server.handle_client_message(StartGame())
    run_local_session(server, clients_by_player_id)

    print()
    print('Endstand:')
    render_public_state(server.build_public_state())
    winner = min(server.state.players, key=lambda p: p.score)
    print(f'Gewonnen hat: {winner.name} (wenigste Hornochsen)')


def run() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        clear_screen()
        print('Abbruch mit Strg+C!')
        return 0
