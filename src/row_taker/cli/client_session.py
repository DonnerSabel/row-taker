from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass

from row_taker.cli.console import CliConsole
from row_taker.cli.render import render_screen, render_public_state, get_prompt
from row_taker.cli.state_machine import reduce_server_message, reduce_user_input
from row_taker.cli.state_models import (
    CliState,
    LobbyStateMain,
    LobbyStateSeatEdit,
    initial_cli_state,
)
from row_taker.cli.terminal import clear_screen
from row_taker.engine.game.state import PublicState
from row_taker.protocol.errors import ConnectionClosed
from row_taker.protocol.messages import (
    IdentityAssigned,
    LobbyView,
    ServerToClientMessage,
)
from row_taker.protocol.transport import ClientTransport


@dataclass(slots=True)
class ClientSession:
    transport: ClientTransport
    ui_client: object | None = None
    interactive: bool = True
    own_client_id: str | None = None

    def run(self) -> PublicState | None:
        return asyncio.run(self.run_async())

    async def run_async(self) -> PublicState | None:
        console = CliConsole()
        state = initial_cli_state(self.own_client_id)
        server_task: asyncio.Task[ServerToClientMessage] | None = asyncio.create_task(
            asyncio.to_thread(self.transport.receive)
        )
        input_task: asyncio.Task[str] | None = None
        input_prompt: str | None = None

        try:
            await self._refresh_screen(console, state)

            while not state.should_exit:
                current_prompt = get_prompt(state) if self.interactive else None

                if current_prompt is None:
                    if input_task is not None:
                        input_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await input_task
                        input_task = None
                        input_prompt = None
                elif input_task is None or input_prompt != current_prompt:
                    if input_task is not None:
                        input_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await input_task
                    input_task = asyncio.create_task(console.read_line())
                    input_prompt = current_prompt

                wait_tasks: set[asyncio.Task[object]] = set()
                if server_task is not None:
                    wait_tasks.add(server_task)
                if input_task is not None:
                    wait_tasks.add(input_task)
                if not wait_tasks:
                    break

                done, _ = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)

                if server_task is not None and server_task in done:
                    try:
                        message = server_task.result()
                    except ConnectionClosed:
                        break

                    state = reduce_server_message(state, message)
                    self.own_client_id = state.own_client_id
                    await self._refresh_screen(console, state)

                    if state.should_exit:
                        break

                    server_task = asyncio.create_task(asyncio.to_thread(self.transport.receive))

                if input_task is not None and input_task in done:
                    try:
                        line = input_task.result()
                    except asyncio.CancelledError:
                        line = None

                    input_task = None
                    input_prompt = None

                    if line is not None:
                        result = reduce_user_input(state, line)
                        state = result.state
                        self.own_client_id = state.own_client_id
                        if result.outbound_message is not None:
                            await asyncio.to_thread(self.transport.send, result.outbound_message)
                        await self._refresh_screen(console, state)

            return state.public_state
        finally:
            if server_task is not None:
                server_task.cancel()
                with suppress(asyncio.CancelledError):
                    await server_task
            if input_task is not None:
                input_task.cancel()
                with suppress(asyncio.CancelledError):
                    await input_task
            await console.close()
            self.transport.close()

    async def _refresh_screen(self, console: CliConsole, state: CliState) -> None:
        await console.render(render_screen(state), get_prompt(state) if self.interactive else None)

    def _handle_message(self, message, latest_lobby, latest_public_state, lobby_mode):
        state = CliState(
            own_client_id=self.own_client_id,
            lobby_view=latest_lobby,
            public_state=latest_public_state,
            mode=self._legacy_mode_to_state(lobby_mode),
        )
        state = reduce_server_message(state, message)
        self.own_client_id = state.own_client_id
        return state.lobby_view, state.public_state, self._state_to_legacy_mode(state), state.should_exit

    def _handle_lobby_command(self, lobby: LobbyView, mode, command: str):
        if mode == ("seat", 0) or (isinstance(mode, tuple) and mode[0] == "seat"):
            if command == "m" and self.own_client_id is None:
                print("Eigene client_id noch nicht zugewiesen. Bitte kurz warten.")
                return ("main", None)

        state = CliState(
            own_client_id=self.own_client_id,
            lobby_view=lobby,
            mode=self._legacy_mode_to_state(mode),
        )
        result = reduce_user_input(state, command)
        self.own_client_id = result.state.own_client_id
        if result.outbound_message is not None:
            self.transport.send(result.outbound_message)
        return self._state_to_legacy_mode(result.state)

    def _render_lobby(self, lobby: LobbyView, mode) -> None:
        clear_screen()
        state = CliState(
            own_client_id=self.own_client_id,
            lobby_view=lobby,
            mode=self._legacy_mode_to_state(mode),
        )
        print(render_screen(state))

    @staticmethod
    def _legacy_mode_to_state(mode):
        state_name, selected = mode
        if state_name == "seat" and selected is not None:
            return LobbyStateSeatEdit(seat_index=selected)
        return LobbyStateMain()

    @staticmethod
    def _state_to_legacy_mode(state: CliState):
        if isinstance(state.mode, LobbyStateSeatEdit):
            return ("seat", state.mode.seat_index)
        return ("main", None)


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return
    clear_screen()
    render_public_state(public_state)
    print("Endstand:")
    ranking = sorted(public_state.players, key=lambda player: (player.score, player.name))
    for place, player in enumerate(ranking, start=1):
        print(f"  {place}. {player.name}: {player.score} Punkte")

