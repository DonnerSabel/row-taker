from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass, replace

from row_taker.cli.console import CliConsole, InputAborted
from row_taker.cli.render import build_view, render_public_state
from row_taker.cli.state_machine import reduce_server_message, reduce_user_input
from row_taker.cli.state_models import CliState, initial_cli_state
from row_taker.cli.terminal import clear_screen
from row_taker.engine.game.state import PublicState
from row_taker.protocol.errors import ConnectionClosed
from row_taker.protocol.messages import ServerToClientMessage
from row_taker.protocol.transport import ClientTransport


@dataclass(slots=True)
class ClientSession:
    transport: ClientTransport
    interactive: bool = True
    own_client_id: str | None = None

    def run(self) -> PublicState | None:
        try:
            return asyncio.run(self.run_async())
        except KeyboardInterrupt:
            return None

    async def run_async(self) -> PublicState | None:
        console = CliConsole()
        state = initial_cli_state(self.own_client_id)
        server_task: asyncio.Task[ServerToClientMessage] | None = asyncio.create_task(
            asyncio.to_thread(self.transport.receive)
        )
        input_task: asyncio.Task[str] | None = None
        input_prompt: str | None = None
        abort_requested = False

        try:
            await self._refresh_screen(console, state)
            while not state.should_exit and not abort_requested:
                current_prompt = build_view(state).prompt if self.interactive else None
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
                        if not state.should_exit and state.session_error is None:
                            state = replace(
                                state,
                                session_error="Die Verbindung zum Server wurde beendet.",
                                exit_on_ack=False,
                            )
                            await self._refresh_screen(console, state)
                            server_task = None
                            continue
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
                    except InputAborted:
                        abort_requested = True
                        line = None

                    input_task = None
                    input_prompt = None

                    if line is not None:
                        result = reduce_user_input(state, line)
                        state = result.state
                        self.own_client_id = state.own_client_id
                        if result.outbound_message is not None:
                            with suppress(Exception):
                                await asyncio.to_thread(self.transport.send, result.outbound_message)
                        if state.should_exit and state.suppress_final_result:
                            break
                        await self._refresh_screen(console, state)

            if state.suppress_final_result or state.session_error is not None:
                return None
            return state.public_state
        finally:
            if server_task is not None:
                server_task.cancel()
                with suppress(asyncio.CancelledError, KeyboardInterrupt):
                    await server_task
            if input_task is not None:
                input_task.cancel()
                with suppress(asyncio.CancelledError, InputAborted, KeyboardInterrupt):
                    await input_task
            await console.close()
            self.transport.close()

    async def _refresh_screen(self, console: CliConsole, state: CliState) -> None:
        view = build_view(state)
        prompt = view.prompt if self.interactive else None
        await console.render(view.body, prompt)


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return
    clear_screen()
    render_public_state(public_state)
    print("Endstand:")
    ranking = sorted(public_state.players, key=lambda player: (player.score, player.name))
    for place, player in enumerate(ranking, start=1):
        print(f"  {place}. {player.name}: {player.score} Punkte")
