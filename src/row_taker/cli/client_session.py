from __future__ import annotations

import select
import sys
from dataclasses import dataclass

from row_taker.cli.render import render_public_state, render_trick_resolution
from row_taker.cli.terminal import clear_screen
from row_taker.clients.cli_client import CliClient
from row_taker.engine.game.state import PublicState
from row_taker.protocol.errors import ConnectionClosed
from row_taker.protocol.messages import (
    AssignSeatToClient,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    CreateLocalBotOnSeat,
    GameStarting,
    IdentityAssigned,
    LobbyActionRejected,
    LobbyStateUpdated,
    LobbyView,
    RequestStartGame,
    ServerError,
    SetDisplayName,
    StateUpdated,
    TrickResolved,
)
from row_taker.protocol.transport import ClientTransport


@dataclass(slots=True)
class ClientSession:
    transport: ClientTransport
    ui_client: CliClient
    interactive: bool = True
    own_client_id: str | None = None

    def run(self) -> PublicState | None:
        latest_public_state: PublicState | None = None
        latest_lobby: LobbyView | None = None
        lobby_mode: tuple[str, int | None] = ("main", None)
        try:
            while True:
                if latest_lobby is not None and not latest_lobby.game_started and self.interactive:
                    self._render_lobby(latest_lobby, lobby_mode)
                    readable, _, _ = select.select([self.transport.sock, sys.stdin], [], [])
                    if self.transport.sock in readable:
                        try:
                            message = self.transport.receive()
                        except ConnectionClosed:
                            return latest_public_state
                        latest_lobby, latest_public_state, lobby_mode, finished = self._handle_message(
                            message,
                            latest_lobby,
                            latest_public_state,
                            lobby_mode,
                        )
                        if finished:
                            return latest_public_state
                        continue
                    if sys.stdin in readable:
                        line = sys.stdin.readline()
                        command = line.strip()
                        lobby_mode = self._handle_lobby_command(latest_lobby, lobby_mode, command)
                        continue
                else:
                    try:
                        message = self.transport.receive()
                    except ConnectionClosed:
                        return latest_public_state
                    latest_lobby, latest_public_state, lobby_mode, finished = self._handle_message(
                        message,
                        latest_lobby,
                        latest_public_state,
                        lobby_mode,
                    )
                    if finished:
                        return latest_public_state
        finally:
            self.transport.close()

    def _handle_message(self, message, latest_lobby, latest_public_state, lobby_mode):
        if isinstance(message, IdentityAssigned):
            self.own_client_id = message.client_id
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, LobbyStateUpdated):
            latest_lobby = message.lobby
            return latest_lobby, latest_public_state, ("main", None), False

        if isinstance(message, LobbyActionRejected):
            print(f"Lobby-Aktion abgelehnt: {message.message}")
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, GameStarting):
            clear_screen()
            print("Spielstart...")
            print()
            latest_lobby = message.lobby
            return latest_lobby, latest_public_state, ("main", None), False

        if isinstance(message, StateUpdated):
            latest_public_state = message.state
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, TrickResolved):
            if latest_public_state is None:
                raise ValueError("missing public state before trick resolution")
            clear_screen()
            render_trick_resolution(latest_public_state, message)
            if self.interactive and not message.game_finished:
                print()
                cont = input("Enter für nächsten Stich, 'q' zum Beenden > ").strip().lower()
                if cont == "q":
                    return latest_lobby, latest_public_state, lobby_mode, True
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, (ChooseCardRequested, ChooseRowRequested)):
            response = self.ui_client.handle_server_message(message)
            if response is not None:
                self.transport.send(response)
            return latest_lobby, latest_public_state, lobby_mode, False

        if isinstance(message, ServerError):
            print(f"Serverfehler: {message.message}")
            return latest_lobby, latest_public_state, lobby_mode, True

        raise TypeError(f"unsupported server message type: {type(message)!r}")

    def _handle_lobby_command(self, lobby: LobbyView, mode: tuple[str, int | None], command: str) -> tuple[str, int | None]:
        state, selected = mode
        if state == "main":
            if command == "n":
                name = input("Neuer Anzeigename > ").strip()
                if name:
                    self.transport.send(SetDisplayName(display_name=name))
                return ("main", None)
            if command == "s":
                seat_value = input(f"Platz wählen [0-{lobby.seat_count - 1}] > ").strip()
                if seat_value.isdigit():
                    seat_index = int(seat_value)
                    if 0 <= seat_index < lobby.seat_count:
                        return ("seat", seat_index)
                return ("main", None)
            if command == "g":
                self.transport.send(RequestStartGame())
                return ("main", None)
            return ("main", None)

        if state == "seat":
            if selected is None:
                return ("main", None)
            if command == "c":
                self.transport.send(ClearSeat(seat_index=selected))
                return ("main", None)
            if command == "m":
                if self.own_client_id is None:
                    print("Eigene client_id noch nicht zugewiesen. Bitte kurz warten.")
                    return ("main", None)
                self.transport.send(AssignSeatToClient(seat_index=selected, target_client_id=self.own_client_id))
                return ("main", None)
            if command == "b":
                name = input("Bot-Name > ").strip()
                if name:
                    self.transport.send(CreateLocalBotOnSeat(seat_index=selected, display_name=name))
                return ("main", None)
            return ("main", None)

        return ("main", None)


    def _render_lobby(self, lobby: LobbyView, mode: tuple[str, int | None]) -> None:
        clear_screen()
        print("Lobby")
        print("=====")
        print()
        for seat in lobby.seats:
            occupant = "frei"
            if seat.occupant_display_name is not None:
                occupant = f"{seat.occupant_display_name} ({seat.occupant_kind})"
            print(f"Platz {seat.seat_index}: {occupant}")
        print()
        print("Teilnehmer")
        print("==========")
        print()
        participants = sorted(
            lobby.participants,
            key=lambda participant: (
                participant.seat_index is None,
                participant.seat_index if participant.seat_index is not None else 9999,
                participant.display_name.lower(),
            ),
        )
        for participant in participants:
            position = f"Platz {participant.seat_index}" if participant.seat_index is not None else "nicht gesetzt"
            marker = " <- du" if participant.client_id == self.own_client_id else ""
            print(f"{participant.display_name} ({participant.participant_kind}, {position}){marker}")
        print()
        if mode[0] == "main":
            print("n = Name ändern, s = Platz wählen, g = Spiel starten")
        else:
            print("m = mich setzen, b = Bot setzen, c = Platz leeren")


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return

    clear_screen()
    render_public_state(public_state)

    print("Endstand:")
    ranking = sorted(public_state.players, key=lambda player: (player.score, player.name))
    for place, player in enumerate(ranking, start=1):
        print(f"  {place}. {player.name}: {player.score} Punkte")
