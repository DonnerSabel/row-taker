from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from row_taker.cli.console import CliConsole, InputAborted
from row_taker.cli.frontend import CliFrontend, set_flash
from row_taker.cli.render import build_view
from row_taker.client.actions import ClientActionAdvancePresentation
from row_taker.client.game_client_core import GameClientCore
from row_taker.client.state import ClientState, initial_client_state
from row_taker.engine.game.state import PublicState
from row_taker.protocol.errors import ConnectionClosed
from row_taker.protocol.messages import ServerToClientMessage
from row_taker.protocol.transport import ClientTransport

logger = logging.getLogger("row_taker.cli.app")


class CliApp:
    def __init__(self, transport: ClientTransport, own_client_id: str | None = None, *, interactive: bool = True, console_factory: type[CliConsole] = CliConsole, initial_state_factory=initial_client_state) -> None:
        self.transport = transport
        self.own_client_id = own_client_id
        self.interactive = interactive
        self.frontend = CliFrontend()
        self.console_factory = console_factory
        self.initial_state_factory = initial_state_factory

    async def run_async(self) -> PublicState | None:
        state = self.initial_state_factory(self.own_client_id)
        core = GameClientCore(state)
        console = self.console_factory()
        server_task: asyncio.Task[ServerToClientMessage] | None = asyncio.create_task(asyncio.to_thread(self.transport.receive))
        input_task: asyncio.Task[str] | None = None
        input_prompt: str | None = None
        abort_requested = False
        try:
            await self._render(console, state)
            while not state.should_exit and not abort_requested:
                state = core.state
                if not self.interactive and core.has_pending_presentation():
                    state, _ = await self._process_action(console, core, ClientActionAdvancePresentation())
                    continue

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
                if not wait_tasks:
                    break
                done, _ = await asyncio.wait(wait_tasks, return_when=asyncio.FIRST_COMPLETED)

                if server_task is not None and server_task in done:
                    try:
                        message = server_task.result()
                    except ConnectionClosed:
                        logger.debug("transport receive ended with ConnectionClosed")
                        if not state.should_exit and state.session_error is None:
                            core.on_transport_closed("Die Verbindung zum Server wurde beendet.")
                            await self._render(console, core.state)
                        server_task = None
                    else:
                        logger.debug("server message received: type=%s", type(message).__name__)
                        update = core.on_server_message(message)
                        state = await self._apply_update(console, core, update)
                        if server_task is not None:
                            server_task = asyncio.create_task(asyncio.to_thread(self.transport.receive))
                    continue

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
                        parsed = self.frontend.handle_text_input(core.state, line)
                        state = parsed.state
                        if parsed.action is None:
                            await self._render(console, state)
                            core.state = state
                        else:
                            core.state = state
                            state, outbounds = await self._process_action(console, core, parsed.action)
                            for outbound in outbounds:
                                logger.debug("sending outbound client message: type=%s", type(outbound).__name__)
                                await asyncio.to_thread(self.transport.send, outbound)
            logger.debug("client main loop exiting: should_exit=%s suppress_final_result=%s session_error=%s", core.state.should_exit, core.state.suppress_final_result, core.state.session_error)
            if core.state.suppress_final_result or core.state.session_error is not None:
                return None
            return core.state.public_state
        finally:
            logger.debug("client session cleanup start: server_task=%s input_task=%s", server_task is not None, input_task is not None)
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

    async def _process_action(self, console: CliConsole, core: GameClientCore, action: object) -> tuple[ClientState, tuple[object, ...]]:
        update = core.on_ui_action(action)
        state = await self._apply_update(console, core, update)
        return state, update.outbound_messages

    async def _apply_update(self, console: CliConsole, core: GameClientCore, update) -> ClientState:
        state = core.state
        if update.local_messages:
            state = set_flash(state, "error", update.local_messages[-1])
            core.state = state
        for message in update.applied_server_messages:
            logger.debug("applying server message: type=%s inbox_remaining=%s pending_presentation=%s", type(message).__name__, len(core.server_inbox), len(core.state.pending_presentation_events))
        await self._render(console, core.state)
        self.own_client_id = core.state.own_client_id
        return core.state

    async def _render(self, console: CliConsole, state: ClientState) -> None:
        view = build_view(state)
        prompt = view.prompt if self.interactive else None
        await console.render(view.body, prompt)

    async def _cancel_input_task(self, input_task: asyncio.Task[str] | None, input_prompt: str | None) -> tuple[asyncio.Task[str] | None, str | None]:
        if input_task is not None:
            input_task.cancel()
            with suppress(asyncio.CancelledError, InputAborted, KeyboardInterrupt):
                await input_task
        return None, None
