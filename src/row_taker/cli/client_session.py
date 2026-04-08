from __future__ import annotations

import select
import socket
import sys
from dataclasses import dataclass
from typing import BinaryIO

from row_taker.cli.render import render_public_state, render_trick_resolution
from row_taker.cli.terminal import clear_screen
from row_taker.clients.cli_client import CliClient
from row_taker.engine.game.state import PublicState
from row_taker.protocol.framing import decode_server_message, encode_client_message
from row_taker.protocol.messages import (
    AssignSeatToClient,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameStarting,
    JoinLobby,
    LobbyActionRejected,
    LobbyParticipantView,
    LobbySeatView,
    LobbyStateUpdated,
    LobbyView,
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
    def connect(cls, host: str, port: int) -> 'SocketTransport':
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
        latest_lobby: LobbyView | None = None
        lobby_mode: tuple[str, int | None] = ('main', None)
        try:
            while True:
                if latest_lobby is not None and not latest_lobby.game_started and self.interactive:
                    self._render_lobby(latest_lobby, lobby_mode)
                    readable, _, _ = select.select([self.transport.sock, sys.stdin], [], [])
                    if self.transport.sock in readable:
                        message = self.transport.receive()
                        if message is None:
                            return latest_public_state
                        latest_lobby, latest_public_state, lobby_mode, finished = self._handle_message(message, latest_lobby, latest_public_state, lobby_mode)
                        if finished:
                            return latest_public_state
                        continue
                    if sys.stdin in readable:
                        line = sys.stdin.readline()
                        command = line.strip()
                        lobby_mode = self._handle_lobby_command(latest_lobby, lobby_mode, command)
                        continue
                else:
                    message = self.transport.receive()
                    if message is None:
                        return latest_public_state
                    latest_lobby, latest_public_state, lobby_mode, finished = self._handle_message(message, latest_lobby, latest_public_state, lobby_mode)
                    if finished:
                        return latest_public_state
        finally:
            self.transport.close()

    def _handle_message(self, message, latest_lobby, latest_public_state, lobby_mode):
        if isinstance(message, LobbyStateUpdated):
            latest_lobby = message.lobby
            return latest_lobby, latest_public_state, ('main', None), False

        if isinstance(message, LobbyActionRejected):
            print(f"Lobby-Aktion abgelehnt: {message.message}")
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, GameStarting):
            clear_screen()
            print('Spielstart...')
            print()
            latest_lobby = message.lobby
            return latest_lobby, latest_public_state, ('main', None), False

        if isinstance(message, StateUpdated):
            latest_public_state = message.state
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, TrickResolved):
            if latest_public_state is None:
                raise ValueError('missing public state before trick resolution')
            clear_screen()
            render_trick_resolution(latest_public_state, message)
            if self.interactive and not message.game_finished:
                print()
                cont = input("Enter für nächsten Stich, 'q' zum Beenden > ").strip().lower()
                if cont == 'q':
                    return latest_lobby, latest_public_state, lobby_mode, True
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, (ChooseCardRequested, ChooseRowRequested)):
            response = self.ui_client.handle_server_message(message)
            if response is not None:
                self.transport.send(response)
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, ServerError):
            print(f'Serverfehler: {message.message}')
            return latest_lobby, latest_public_state, lobby_mode, True

        raise TypeError(f'unsupported server message type: {type(message)!r}')

    def _handle_lobby_command(self, lobby: LobbyView, mode: tuple[str, int | None], command: str) -> tuple[str, int | None]:
        state, selected = mode
        if state == 'main':
            if command == 'n':
                name = input('Neuer Anzeigename > ').strip()
                if name:
                    self.transport.send(SetDisplayName(display_name=name))
                return ('main', None)
            if command == 's':
                seat_raw = input(f'Seat auswählen (1-{lobby.seat_count}) > ').strip()
                if seat_raw.isdigit():
                    seat_index = int(seat_raw) - 1
                    if 0 <= seat_index < lobby.seat_count:
                        return ('seat', seat_index)
                return ('main', None)
            if command == 'g':
                self.transport.send(RequestStartGame())
                return ('main', None)
            return ('main', None)

        if selected is None:
            return ('main', None)

        if state == 'seat':
            if command == 'x':
                return ('main', None)
            if command == 'f':
                self.transport.send(ClearSeat(seat_index=selected))
                return ('main', None)
            if command == 'h':
                return ('seat_human', selected)
            if command == 'b':
                return ('seat_bot', selected)
            return ('seat', selected)

        if state == 'seat_human':
            humans = [participant for participant in lobby.participants if participant.participant_kind == 'human']
            if command.isdigit():
                idx = int(command) - 1
                if 0 <= idx < len(humans):
                    self.transport.send(AssignSeatToClient(seat_index=selected, target_client_id=humans[idx].client_id))
            return ('main', None)

        if state == 'seat_bot':
            bot_name = command.strip() or f'Bot_{selected + 1}'
            self.transport.send(CreateLocalBotOnSeat(seat_index=selected, display_name=bot_name))
            return ('main', None)

        return ('main', None)

    def _render_lobby(self, lobby: LobbyView, mode: tuple[str, int | None]) -> None:
        clear_screen()
        _print_lobby_state(lobby)
        state, selected = mode
        if state == 'main':
            print('(n)ame, (s)eat bearbeiten, (g)o > ', end='', flush=True)
            return
        if selected is None:
            print('(n)ame, (s)eat bearbeiten, (g)o > ', end='', flush=True)
            return
        occupant = _seat_by_index(lobby, selected)
        print(f'Ausgewählter Seat: {selected + 1}')
        if occupant is None or occupant.occupant_client_id is None:
            print('Aktuell: [frei]')
        else:
            label = 'Mensch' if occupant.occupant_kind == 'human' else 'Bot'
            print(f'Aktuell: [{label}] {occupant.occupant_display_name}')
        print()
        if state == 'seat':
            print('(h)uman setzen, (b)ot setzen, (f)reigeben, (x) zurück > ', end='', flush=True)
            return
        if state == 'seat_human':
            humans = [participant for participant in lobby.participants if participant.participant_kind == 'human']
            print('Verfügbare menschliche Clients:')
            for idx, participant in enumerate(humans, start=1):
                suffix = '' if participant.seat_index is None else f' (derzeit Seat {participant.seat_index + 1})'
                print(f'  {idx}: {participant.display_name}{suffix}')
            print()
            print('Nummer wählen > ', end='', flush=True)
            return
        if state == 'seat_bot':
            print('Bot-Name > ', end='', flush=True)
            return


def _seat_by_index(lobby: LobbyView, seat_index: int) -> LobbySeatView | None:
    for seat in lobby.seats:
        if seat.seat_index == seat_index:
            return seat
    return None


def _print_lobby_state(lobby: LobbyView) -> None:
    print('Lobby')
    print('=====')
    print('Verbundene Teilnehmer:')
    for participant in lobby.participants:
        kind_label = 'Mensch' if participant.participant_kind == 'human' else 'Bot'
        suffix = '' if participant.seat_index is None else f' [Seat {participant.seat_index + 1}]'
        print(f'  - {participant.display_name} ({kind_label}){suffix}')
    print()
    print('Seats:')
    for seat in lobby.seats:
        label = str(seat.seat_index + 1)
        if seat.occupant_client_id is None:
            text = '[frei]'
        elif seat.occupant_kind == 'human':
            text = f'[Mensch] {seat.occupant_display_name}'
        else:
            text = f'[Bot] {seat.occupant_display_name}'
        print(f'  {label}: {text}')
    print()


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return

    clear_screen()
    render_public_state(public_state)

    print('Endstand:')
    ranking = sorted(public_state.players, key=lambda player: (player.score, player.name))
    for place, player in enumerate(ranking, start=1):
        print(f'  {place}. {player.name}: {player.score} Punkte')
