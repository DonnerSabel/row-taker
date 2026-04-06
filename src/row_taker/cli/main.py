from __future__ import annotations

import random

from row_taker.cli.create_match_config import create_match_config
from row_taker.cli.local_runner import print_final_result, run_local_game
from row_taker.cli.terminal import clear_screen
from row_taker.clients.cli_client import CliClient
from row_taker.clients.random_bot_client import RandomBotClient
from row_taker.engine.lobby.config import ClientKind
from row_taker.protocol.messages import ConfigureLobby, StartGame
from row_taker.server.local_server import LocalServer


def main() -> None:
    rng = random.Random()

    clear_screen()
    print("Row-Taker – CLI (Hotseat)")
    print()

    match_config = create_match_config()
    server = LocalServer(rng=rng)
    server.handle_client_message(ConfigureLobby(match_config=match_config))

    clients_by_player_id = {}
    for seat_index, seat in enumerate(match_config.seats):
        player_id = f"player-{seat_index}"
        if seat.kind == ClientKind.HUMAN:
            clients_by_player_id[player_id] = CliClient()
        elif seat.kind == ClientKind.RANDOM_BOT:
            clients_by_player_id[player_id] = RandomBotClient(rng=rng)
        else:
            raise ValueError(f"unsupported client kind: {seat.kind!r}")

    server.handle_client_message(StartGame())
    run_local_game(server, clients_by_player_id)
    print_final_result(server)


def run() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        clear_screen()
        print("Abbruch mit Strg+C!")
        return 0
