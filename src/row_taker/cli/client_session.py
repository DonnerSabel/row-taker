from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, replace

from row_taker.cli.console import CliConsole, InputAborted
from row_taker.cli.render import build_view, render_public_state
from row_taker.cli.state_machine import (
    advance_presentation_queue,
    reduce_server_message,
    reduce_user_input,
)
from row_taker.cli.state_models import CliState, initial_cli_state
from row_taker.cli.terminal import clear_screen
from row_taker.engine.game.state import PublicState
from row_taker.protocol.errors import ConnectionClosed
from row_taker.protocol.messages import ServerToClientMessage, get_game_message_revision
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
        server_inbox: deque[ServerToClientMessage] = deque()
        server_task: asyncio.Task[ServerToClientMessage] | None = asyncio.create_task(
            asyncio.to_thread(self.transport.receive)
        )
        input_task: asyncio.Task[str] | None = None
        input_prompt: str | None = None
        presentation_task: asyncio.Task[None] | None = None
        abort_requested = False

        try:
            await self._refresh_screen(console, state)
            while not state.should_exit and not abort_requested:
                state = self._apply_pending_server_messages(state, server_inbox)
                await self._refresh_screen(console, state)
                if state.should_exit:
                    input_task, input_prompt = await self._cancel_input_task(input_task, input_prompt)
                    break

                presentation_task = self._ensure_presentation_task(state, presentation_task)
                current_prompt = build_view(state).prompt if self.interactive else None
                if current_prompt is None:
                    input_task, input_prompt = await self._cancel_input_task(input_task, input_prompt)
                elif input_task is None or input_prompt != current_prompt:
                    input_task, input_prompt = await self._cancel_input_task(input_task, input_prompt)
                    input_task = asyncio.create_task(console.read_line())
                    input_prompt = current_prompt

                wait_tasks: set[asyncio.Task[object]] = set()
                if server_task is not None:
                    wait_tasks.add(server_task)
                if input_task is not None:
                    wait_tasks.add(input_task)
                if presentation_task is not None:
                    wait_tasks.add(presentation_task)
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
                    server_inbox.append(message)
                    revision = get_game_message_revision(message)
                    if revision is not None:
                        state = replace(state, received_game_revision=revision)
                    server_task = asyncio.create_task(asyncio.to_thread(self.transport.receive))

                if presentation_task is not None and presentation_task in done:
                    presentation_task = None
                    state = advance_presentation_queue(state)
                    await self._refresh_screen(console, state)

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
                            input_task, input_prompt = await self._cancel_input_task(input_task, input_prompt)
                            await self._refresh_screen(console, state)
                            break
                        await self._refresh_screen(console, state)

            if state.suppress_final_result or state.session_error is not None:
                return None
            return state.public_state
        finally:
            if presentation_task is not None:
                presentation_task.cancel()
                with suppress(asyncio.CancelledError, KeyboardInterrupt):
                    await presentation_task
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

    def _ensure_presentation_task(
        self,
        state: CliState,
        presentation_task: asyncio.Task[None] | None,
    ) -> asyncio.Task[None] | None:
        if not state.pending_resolution_lines:
            if presentation_task is not None:
                presentation_task.cancel()
            return None
        if presentation_task is None or presentation_task.done():
            return asyncio.create_task(asyncio.sleep(0.15))
        return presentation_task

    def _apply_pending_server_messages(
        self,
        state: CliState,
        server_inbox: deque[ServerToClientMessage],
    ) -> CliState:
        while server_inbox:
            message = server_inbox.popleft()
            state = reduce_server_message(state, message)
            revision = get_game_message_revision(message)
            if revision is not None:
                state = replace(state, applied_game_revision=revision)
            self.own_client_id = state.own_client_id
            if state.should_exit:
                break
        return state

    async def _refresh_screen(self, console: CliConsole, state: CliState) -> None:
        view = build_view(state)
        prompt = view.prompt if self.interactive else None
        await console.render(view.body, prompt)

    async def _cancel_input_task(
        self,
        input_task: asyncio.Task[str] | None,
        input_prompt: str | None,
    ) -> tuple[asyncio.Task[str] | None, str | None]:
        if input_task is not None:
            input_task.cancel()
            with suppress(asyncio.CancelledError, InputAborted, KeyboardInterrupt):
                await input_task
        return None, None


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return
    clear_screen()
    render_public_state(public_state)
    print("Endstand:")
    ranking = sorted(public_state.players, key=lambda player: (player.score, player.name))
    for place, player in enumerate(ranking, start=1):
        print(f"  {place}. {player.name}: {player.score} Punkte")
