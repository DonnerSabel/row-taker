from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import BinaryIO

from row_taker.cli.render import render_public_state, render_trick_resolution
from row_taker.cli.terminal import clear_screen
from row_taker.clients.cli_client import CliClient
from row_taker.engine.game.state import PublicState
from row_taker.protocol.framing import decode_server_message, encode_client_message
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ClientToServerMessage,
    GameStarting,
    LobbyStateUpdated,
    ServerError,
    StateUpdated,
    TrickResolved,
)


@dataclass(slots=True)
class SocketTransport:
    sock: socket.socket
    reader: BinaryIO
    writer: BinaryIO

    @classmethod
    def connect(cls, host: str, port: int) -> "SocketTransport":
        sock = socket.create_connection((host, port))
        return cls(
            sock=sock,
            reader=sock.makefile("rb"),
            writer=sock.makefile("wb"),
        )

    def send(self, message: ClientToServerMessage) -> None:
        self.writer.write(encode_client_message(message))
        self.writer.flush()

    def receive(self):
        line = self.reader.readline()
        if not line:
            return None
        return decode_server_message(line)

    def close(self) -> None:
        try:
            self.writer.close()
        finally:
            try:
                self.reader.close()
            finally:
                self.sock.close()


@dataclass(slots=True)
class ClientSession:
    transport: SocketTransport
    ui_client: CliClient
    interactive: bool = True

    def run(self) -> PublicState | None:
        latest_public_state: PublicState | None = None
        try:
            while True:
                message = self.transport.receive()
                if message is None:
                    return latest_public_state

                if isinstance(message, LobbyStateUpdated):
                    clear_screen()
                    print("Lobby konfiguriert.")
                    if message.lobby_state.match_config is not None:
                        print(f"Spieler: {message.lobby_state.match_config.player_count}")
                    print()
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
                    if self.interactive and not message.game_finished:
                        print()
                        cont = input("Enter für nächsten Stich, 'q' zum Beenden > ").strip().lower()
                        if cont == 'q':
                            return latest_public_state
                    continue

                if isinstance(message, (ChooseCardRequested, ChooseRowRequested)):
                    response = self.ui_client.handle_server_message(message)
                    if response is not None:
                        self.transport.send(response)
                    continue

                if isinstance(message, ServerError):
                    print(f"Serverfehler: {message.message}")
                    return latest_public_state

                raise TypeError(f"unsupported server message type: {type(message)!r}")
        finally:
            self.transport.close()


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return
    print()
    print("Endstand:")
    render_public_state(public_state)
    winner = min(public_state.players, key=lambda p: p.score)
    print(f"Gewonnen hat: {winner.name} (wenigste Hornochsen)")
