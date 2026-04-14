from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace

from row_taker.client.actions import UiAction
from row_taker.client.core_reducer import apply_ui_action, reduce_server_message
from row_taker.client.core_state import ClientCoreState, initial_client_core_state
from row_taker.protocol.messages import ServerError, ServerToClientMessage, SessionEnded, get_game_message_revision


@dataclass(frozen=True, slots=True)
class CoreUpdate:
    state: ClientCoreState
    applied_server_messages: tuple[ServerToClientMessage, ...] = ()
    outbound_messages: tuple[object, ...] = ()
    local_messages: tuple[str, ...] = ()
    deferred: bool = False


class GameClientCore:
    """GUI-neutral client core.

    This class owns:
    - server inbox
    - defer logic while presentation is pending
    - revision bookkeeping
    - UI action application
    - continuing ready server-flow after local actions
    """

    def __init__(self, state: ClientCoreState | None = None) -> None:
        self.state = initial_client_core_state() if state is None else state
        self._server_inbox: deque[ServerToClientMessage] = deque()

    @property
    def server_inbox(self) -> tuple[ServerToClientMessage, ...]:
        return tuple(self._server_inbox)

    def receive_server_message(self, message: ServerToClientMessage) -> CoreUpdate:
        self._server_inbox.append(message)
        revision = get_game_message_revision(message)
        if revision is not None:
            self.state = replace(self.state, received_game_revision=revision)
        return self._drain_server_inbox()

    def apply_action(self, action: UiAction) -> CoreUpdate:
        result = apply_ui_action(self.state, action)
        self.state = result.state
        return CoreUpdate(
            state=self.state,
            outbound_messages=(result.outbound_message,) if result.outbound_message is not None else (),
            local_messages=(result.local_message,) if result.local_message is not None else (),
        )

    def continue_ready_flow(self) -> CoreUpdate:
        return self._drain_server_inbox()

    def has_pending_presentation(self) -> bool:
        return bool(self.state.pending_presentation_events)

    def has_pending_server_messages(self) -> bool:
        return bool(self._server_inbox)

    def _drain_server_inbox(self) -> CoreUpdate:
        applied_messages: list[ServerToClientMessage] = []
        deferred = False

        while self._server_inbox:
            next_message = self._server_inbox[0]
            if self._should_defer_server_message_application(next_message):
                deferred = True
                break

            message = self._server_inbox.popleft()
            self.state = reduce_server_message(self.state, message)

            revision = get_game_message_revision(message)
            if revision is not None:
                self.state = replace(self.state, applied_game_revision=revision)

            applied_messages.append(message)

        return CoreUpdate(
            state=self.state,
            applied_server_messages=tuple(applied_messages),
            deferred=deferred,
        )

    def _should_defer_server_message_application(self, message: ServerToClientMessage) -> bool:
        if not self.state.pending_presentation_events:
            return False
        return not isinstance(message, (SessionEnded, ServerError))
