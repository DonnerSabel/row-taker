from __future__ import annotations

from row_taker.cli.render import render_public_state, render_trick_resolution
from row_taker.cli.terminal import clear_screen
from row_taker.clients.client import Client
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    GameStarting,
    LobbyStateUpdated,
    StateUpdated,
    TrickResolved,
)
from row_taker.server.local_server import LocalServer


def run_local_game(server: LocalServer, clients_by_player_id: dict[str, Client], *, interactive: bool = True) -> None:
    latest_public_state = None

    while True:
        messages = server.drain_outbox()
        if not messages:
            return

        for message in messages:
            if isinstance(message, LobbyStateUpdated):
                continue

            if isinstance(message, GameStarting):
                clear_screen()
                print("Spielstart...")
                print()
                continue

            if isinstance(message, StateUpdated):
                latest_public_state = message.state
                continue

            if isinstance(message, TrickResolved):
                if latest_public_state is None:
                    raise ValueError("missing public state before trick resolution")
                clear_screen()
                render_trick_resolution(latest_public_state, message)
                if message.game_finished:
                    continue
                if interactive:
                    print()
                    cont = input("Enter für nächsten Stich, 'q' zum Beenden > ").strip().lower()
                    if cont == 'q':
                        raise KeyboardInterrupt
                continue

            if isinstance(message, (ChooseCardRequested, ChooseRowRequested)):
                client = clients_by_player_id[message.player_id]
                response = client.handle_server_message(message)
                if response is not None:
                    server.handle_client_message(response)
                continue

            raise TypeError(f"unsupported server message type: {type(message)!r}")


def print_final_result(server: LocalServer) -> None:
    print()
    print("Endstand:")
    render_public_state(server.build_public_state())
    winner = min(server.state.players, key=lambda p: p.score)
    print(f"Gewonnen hat: {winner.name} (wenigste Hornochsen)")
