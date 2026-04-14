from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import replace

from row_taker.cli.console import CliConsole, InputAborted
from row_taker.cli.frontend import CliFrontend, mark_server_error, mark_session_ended
from row_taker.cli.render import build_view
from row_taker.cli.state_machine import reduce_user_input
from row_taker.cli.state_models import CliState, apply_client_core_state, initial_cli_state
from row_taker.client.actions import UiActionAdvancePresentation
from row_taker.client.game_client_core import GameClientCore
from row_taker.engine.game.state import PublicState
from row_taker.protocol.errors import ConnectionClosed
from row_taker.protocol.messages import ServerError, ServerToClientMessage, SessionEnded
from row_taker.protocol.transport import ClientTransport

logger = logging.getLogger("row_taker.cli.runtime")


class CliRuntime:
    def __init__(
        self,
        transport: ClientTransport,
        own_client_id: str | None = None,
        *,
        interactive: bool = True,
        console_factory: type[CliConsole] = CliConsole,
        initial_state_factory=initial_cli_state,
    ) -> None:
        self.transport = transport
        self.own_client_id = own_client_id
        self.interactive = interactive
        self.frontend = CliFrontend()
        self.console_factory = console_factory
        self.initial_state_factory = initial_state_factory

    async def run_async(self) -> PublicState | None:
        state = self.initial_state_factory(self.own_client_id)
        core = GameClientCore(state.core_state)
        console = self.console_factory()
        server_task: asyncio.Task[ServerToClientMessage] | None = asyncio.create_task(asyncio.to_thread(self.transport.receive))
        input_task: asyncio.Task[str] | None = None
        input_prompt: str | None = None
        abort_requested = False

        try:
            while not state.should_exit and not abort_requested:
                state = await self._drain_core_messages(core, state, console)
                if state.should_exit:
                    input_task, input_prompt = await self._cancel_input_task(input_task, input_prompt)
                    break

                await self._refresh_screen(console, state)

                if not self.interactive and core.has_pending_presentation():
                    logger.debug("auto-advancing pending presentation event: pending=%s", len(core.state.pending_presentation_events))
                    result = core.apply_action(UiActionAdvancePresentation())
                    state = self._apply_core_state(state, core.state)
                    state = self.frontend.sync_to_core(state)
                    if result.outbound_message is not None:
                        await asyncio.to_thread(self.transport.send, result.outbound_message)
                    await self._refresh_screen(console, state)
                    continue

                current_prompt = build_view(state).prompt if self.interactive else None
                if current_prompt is None:
                    input_task, input_prompt = await self._cancel_input_task(input_task, input_prompt)
                elif input_task is None or input_prompt != current_prompt:
                    input_task, input_prompt = await self._replace_input_task(input_task, current_prompt, console)

                wait_tasks: set[asyncio.Task[object]] = set()
                if server_task is not None:
                    wait_tasks.add(server_task)
                if input_task is not None:
                    wait_tasks.add(input_task)
                if not wait_tasks:
                    break

                done, _ = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)

                if server_task is not None and server_task in done:
                    state, server_task = await self._handle_server_task(core, state, console, server_task)
                    continue

                if input_task is not None and input_task in done:
                    state, abort_requested = await self._handle_input_task(core, state, console, input_task)
                    input_task = None
                    input_prompt = None
                    continue

            logger.debug(
                "client main loop exiting: should_exit=%s suppress_final_result=%s session_error=%s",
                state.should_exit,
                state.suppress_final_result,
                state.session_error,
            )
            if state.suppress_final_result or state.session_error is not None:
                return None
            return state.public_state
        finally:
            await self._cleanup(console, server_task, input_task)

    async def _drain_core_messages(self, core: GameClientCore, state: CliState, console: CliConsole) -> CliState:
        while core.has_pending_server_messages() and not state.should_exit:
            next_message = core.server_inbox[0]
            if core.should_defer_server_message_application(next_message):
                break
            message, _applied = core.apply_next_server_message()
            assert message is not None
            logger.debug(
                "applying server message: type=%s inbox_remaining=%s pending_presentation=%s",
                type(message).__name__,
                len(core.server_inbox),
                len(core.state.pending_presentation_events),
            )
            state = self._apply_core_state(state, core.state)
            state = self.frontend.sync_to_core(state)
            if isinstance(message, SessionEnded):
                state = mark_session_ended(state)
            elif isinstance(message, ServerError):
                state = mark_server_error(state)
            await self._refresh_screen(console, state)
        return state

    async def _handle_server_task(
        self,
        core: GameClientCore,
        state: CliState,
        console: CliConsole,
        server_task: asyncio.Task[ServerToClientMessage],
    ) -> tuple[CliState, asyncio.Task[ServerToClientMessage] | None]:
        try:
            message = server_task.result()
        except ConnectionClosed:
            logger.debug("transport receive ended with ConnectionClosed")
            if not state.should_exit and state.session_error is None:
                core.state = replace(core.state, session_error="Die Verbindung zum Server wurde beendet.")
                state = self._apply_core_state(state, core.state)
                state = mark_server_error(state)
                await self._refresh_screen(console, state)
                return state, None
            return state, None

        logger.debug("server message received: type=%s", type(message).__name__)
        logger.debug("server message queued from transport: type=%s", type(message).__name__)
        core.enqueue_server_message(message)
        revision = core.state.received_game_revision
        if revision is not None:
            logger.debug(
                "server message enqueued: type=%s revision=%s inbox_size=%s applied_revision=%s",
                type(message).__name__,
                revision,
                len(core.server_inbox),
                core.state.applied_game_revision,
            )
        return state, asyncio.create_task(asyncio.to_thread(self.transport.receive))

    async def _handle_input_task(
        self,
        core: GameClientCore,
        state: CliState,
        console: CliConsole,
        input_task: asyncio.Task[str],
    ) -> tuple[CliState, bool]:
        abort_requested = False
        try:
            line = input_task.result()
        except asyncio.CancelledError:
            line = None
        except InputAborted:
            abort_requested = True
            line = None

        if line is None:
            return state, abort_requested

        result = reduce_user_input(state, line)
        state = result.state
        core.state = state.core_state
        self.own_client_id = state.own_client_id
        if result.outbound_message is not None:
            logger.debug("sending outbound client message: type=%s", type(result.outbound_message).__name__)
            with suppress(Exception):
                await asyncio.to_thread(self.transport.send, result.outbound_message)
        if state.should_exit and state.suppress_final_result:
            await self._refresh_screen(console, state)
            return state, abort_requested
        await self._refresh_screen(console, state)
        return state, abort_requested

    def _apply_core_state(self, state: CliState, core_state) -> CliState:
        state = apply_client_core_state(state, core_state)
        self.own_client_id = state.own_client_id
        return state

    async def _refresh_screen(self, console: CliConsole, state: CliState) -> None:
        view = build_view(state)
        prompt = view.prompt if self.interactive else None
        await console.render(view.body, prompt)

    async def _replace_input_task(
        self,
        input_task: asyncio.Task[str] | None,
        prompt: str,
        console: CliConsole,
    ) -> tuple[asyncio.Task[str] | None, str | None]:
        await self._cancel_input_task(input_task, None)
        return asyncio.create_task(console.read_line()), prompt

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

    async def _cleanup(
        self,
        console: CliConsole,
        server_task: asyncio.Task[ServerToClientMessage] | None,
        input_task: asyncio.Task[str] | None,
    ) -> None:
        logger.debug(
            "client session cleanup start: server_task=%s input_task=%s",
            server_task is not None,
            input_task is not None,
        )
        logger.debug("transport close requested")
        self.transport.close()
        if server_task is not None:
            logger.debug("server receive task cancel requested")
            server_task.cancel()
            logger.debug("awaiting server receive task shutdown")
            with suppress(asyncio.CancelledError, KeyboardInterrupt, ConnectionClosed):
                await server_task
            logger.debug("server receive task shutdown complete")
        else:
            logger.debug("server receive task shutdown skipped")
        if input_task is not None:
            logger.debug("client input task cancel requested")
            input_task.cancel()
            logger.debug("awaiting client input task shutdown")
            with suppress(asyncio.CancelledError, InputAborted, KeyboardInterrupt):
                await input_task
            logger.debug("client input task shutdown complete")
        else:
            logger.debug("client input task shutdown skipped")
        logger.debug("console close start")
        await console.close()
        logger.debug("console close complete")
        logger.debug("client session cleanup finished")
