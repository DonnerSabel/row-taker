from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import BinaryIO

from row_taker.cli.render import render_public_state, render_trick_resolution
from row_taker.cli.terminal import clear_screen
from row_taker.clients.cli_client import CliClient
from row_taker.engine.game.state import PublicState
from row_taker.engine.lobby.config import ClientKind
from row_taker.engine.lobby.state import LobbyState
from row_taker.protocol.framing import decode_server_message, encode_client_message
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ChooseSeat,
    ClearBotSeats,
    ClientToServerMessage,
    FillEmptySeatsWithBots,
    GameStarting,
    JoinLobby,
    LeaveSeat,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    ServerError,
    SetDisplayName,
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
        return cls(sock=sock, reader=sock.makefile('rb'), writer=sock.makefile('wb'))

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
                    self._handle_lobby_state_updated(message.lobby_state)
                    continue

                if isinstance(message, LobbyActionRejected):
                    print(f"Lobby-Aktion abgelehnt: {message.message}")
                    continue

                if isinstance(message, GameStarting):
                    clear_screen()
                    print('Spielstart...')
                    print()
                    continue

                if isinstance(message, StateUpdated):
                    latest_public_state = message.state
                    continue

                if isinstance(message, TrickResolved):
                    if latest_public_state is None:
                        raise ValueError('missing public state before trick resolution')
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
                    print(f'Serverfehler: {message.message}')
                    return latest_public_state

                raise TypeError(f'unsupported server message type: {type(message)!r}')
        finally:
            self.transport.close()

    def _handle_lobby_state_updated(self, lobby_state: LobbyState) -> None:
        clear_screen()
        _print_lobby_state(lobby_state)
        if not self.interactive or lobby_state.game_started:
            return
        action = input('(n)ame, (s)eat, (l)eave, (b)ots füllen, (c) bots löschen, (g)o, Enter=warte > ').strip().lower()
        if not action:
            return
        if action == 'n':
            name = input('Neuer Anzeigename > ').strip()
            if name:
                self.transport.send(SetDisplayName(display_name=name))
            return
        if action == 's':
            seat_raw = input(f'Seat wählen (1-{lobby_state.seat_count}) > ').strip()
            if seat_raw.isdigit():
                self.transport.send(ChooseSeat(seat_index=int(seat_raw) - 1))
            return
        if action == 'l':
            self.transport.send(LeaveSeat())
            return
        if action == 'b':
            self.transport.send(FillEmptySeatsWithBots())
            return
        if action == 'c':
            self.transport.send(ClearBotSeats())
            return
        if action == 'g':
            self.transport.send(RequestStartGame())
            return


def _print_lobby_state(lobby_state: LobbyState) -> None:
    print('Lobby')
    print('=====')
    print('Verbundene Clients:')
    for client in lobby_state.clients:
        print(f'  - {client.display_name}')
    print()
    print('Seats:')
    for seat in lobby_state.seats:
        label = str(seat.seat_index + 1)
        if seat.kind is None:
            text = '[frei]'
        elif seat.kind == ClientKind.HUMAN:
            text = f'[Mensch] {seat.name}'
        else:
            text = f'[Bot] {seat.name}'
        print(f'  {label}: {text}')
    print()


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return
    print()
    print('Endstand:')
    render_public_state(public_state)
    winner = min(public_state.players, key=lambda p: p.score)
    print(f'Gewonnen hat: {winner.name} (wenigste Hornochsen)')
