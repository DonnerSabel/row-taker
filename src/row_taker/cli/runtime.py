from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from row_taker.cli.console import CliConsole, InputAborted
from row_taker.cli.frontend import CliFrontend, mark_server_error, mark_session_ended, set_flash
from row_taker.cli.render import build_view
from row_taker.cli.state_models import CliState, apply_client_core_state, initial_cli_state
from row_taker.client.actions import UiActionAdvancePresentation
from row_taker.client.game_client_core import CoreUpdate, GameClientCore
from row_taker.engine.game.state import PublicState
from row_taker.protocol.errors import ConnectionClosed
from row_taker.protocol.messages import ServerError, ServerToClientMessage, SessionEnded
from row_taker.protocol.transport import ClientTransport

logger = logging.getLogger("row_taker.cli.runtime")


class CliRuntime:
    """CLI host around the GUI-neutral GameClientCore."""

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

        server_task: asyncio.Task[ServerToClientMessage] | None = self._spawn_server_task()
        input_task: asyncio.Task[str] | None = None
        input_prompt: str | None = None
        abort_requested = False

        try:
            await self._render(console, state)

            while not state.should_exit and not abort_requested:
                if not self.interactive and core.has_pending_presentation():
                    state, _ = await self._process_action(console, core, state, UiActionAdvancePresentation())
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

    def _spawn_server_task(self) -> asyncio.Task[ServerToClientMessage]:
        return asyncio.create_task(asyncio.to_thread(self.transport.receive))

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
                update = core.on_transport_closed("Die Verbindung zum Server wurde beendet.")
                state = await self._apply_core_update(console, core, state, update)
                state = mark_server_error(state)
                await self._render(console, state)
            return state, None

        logger.debug("server message received: type=%s", type(message).__name__)
        update = core.on_server_message(message)
        state = await self._apply_core_update(console, core, state, update)
        return state, self._spawn_server_task()

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

        parsed = self.frontend.handle_text_input(state, line)
        state = parsed.state

        if parsed.action is None:
            await self._render(console, state)
            return state, abort_requested

        state, outbound_messages = await self._process_action(console, core, state, parsed.action)

        for outbound_message in outbound_messages:
            logger.debug("sending outbound client message: type=%s", type(outbound_message).__name__)
            await asyncio.to_thread(self.transport.send, outbound_message)

        return state, abort_requested

    async def _process_action(
        self,
        console: CliConsole,
        core: GameClientCore,
        state: CliState,
        action: object,
    ) -> tuple[CliState, tuple[object, ...]]:
        update = core.on_ui_action(action)
        state = await self._apply_core_update(console, core, state, update)
        return state, update.outbound_messages

    async def _apply_core_update(
        self,
        console: CliConsole,
        core: GameClientCore,
        state: CliState,
        update: CoreUpdate,
    ) -> CliState:
        state = self._sync_state_from_core(state, core)

        if update.local_messages:
            state = set_flash(state, "error", update.local_messages[-1])
        elif update.applied_server_messages or update.outbound_messages:
            state = self.frontend.clear_flash(state)

        if not update.applied_server_messages:
            await self._render(console, state)
            return state

        for message in update.applied_server_messages:
            logger.debug(
                "applying server message: type=%s inbox_remaining=%s pending_presentation=%s",
                type(message).__name__,
                len(core.server_inbox),
                len(core.state.pending_presentation_events),
            )
            state = self._sync_state_from_core(state, core)
            state = self._apply_cli_side_effects(state, message)
            await self._render(console, state)

        return state

    async def _render(self, console: CliConsole, state: CliState) -> None:
        view = build_view(state)
        await console.render(view.body, view.prompt)

    def _sync_state_from_core(self, state: CliState, core: GameClientCore) -> CliState:
        state = apply_client_core_state(state, core.state)
        return self.frontend.sync_to_core(state)

    def _apply_cli_side_effects(self, state: CliState, message: ServerToClientMessage) -> CliState:
        match message:
            case SessionEnded():
                return mark_session_ended(state)
            case ServerError():
                return mark_server_error(state)
            case _:
                return state

    async def _replace_input_task(
        self,
        input_task: asyncio.Task[str] | None,
        prompt: str,
        console: CliConsole,
    ) -> tuple[asyncio.Task[str], str]:
        input_task, _ = await self._cancel_input_task(input_task, None)
        return asyncio.create_task(console.read_line()), prompt

    async def _cancel_input_task(
        self,
        input_task: asyncio.Task[str] | None,
        _input_prompt: str | None,
    ) -> tuple[asyncio.Task[str] | None, str | None]:
        if input_task is None:
            return None, None
        input_task.cancel()
        with suppress(asyncio.CancelledError):
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
        await asyncio.to_thread(self.transport.close)

        if server_task is not None:
            logger.debug("server receive task cancel requested")
            server_task.cancel()
            logger.debug("awaiting server receive task shutdown")
            with suppress(asyncio.CancelledError, ConnectionClosed):
                await server_task
            logger.debug("server receive task shutdown complete")

        if input_task is not None:
            logger.debug("client input task cancel requested")
            input_task.cancel()
            with suppress(asyncio.CancelledError):
                await input_task
            logger.debug("client input task shutdown complete")
        else:
            logger.debug("client input task shutdown skipped")

        logger.debug("console close start")
        await console.close()
        logger.debug("console close complete")
        logger.debug("client session cleanup finished")
