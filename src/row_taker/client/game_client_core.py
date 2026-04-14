from __future__ import annotations

from collections import deque
from dataclasses import replace

from row_taker.client.actions import UiAction
from row_taker.client.core_reducer import CoreActionResult, apply_ui_action, reduce_server_message
from row_taker.client.core_state import ClientCoreState, initial_client_core_state
from row_taker.protocol.messages import ServerError, ServerToClientMessage, SessionEnded, get_game_message_revision


class GameClientCore:
    def __init__(self, state: ClientCoreState | None = None) -> None:
        self.state = initial_client_core_state() if state is None else state
        self._server_inbox: deque[ServerToClientMessage] = deque()

    @property
    def server_inbox(self) -> deque[ServerToClientMessage]:
        return self._server_inbox

    def enqueue_server_message(self, message: ServerToClientMessage) -> None:
        self._server_inbox.append(message)
        revision = get_game_message_revision(message)
        if revision is not None:
            self.state = replace(self.state, received_game_revision=revision)

    def has_pending_server_messages(self) -> bool:
        return bool(self._server_inbox)

    def has_pending_presentation(self) -> bool:
        return bool(self.state.pending_presentation_events)

    def should_defer_server_message_application(self, message: ServerToClientMessage) -> bool:
        if not self.state.pending_presentation_events:
            return False
        return not self._is_immediate_server_message(message)

    def apply_next_server_message(self) -> tuple[ServerToClientMessage | None, bool]:
        if not self._server_inbox:
            return None, False
        next_message = self._server_inbox[0]
        if self.should_defer_server_message_application(next_message):
            return None, False
        message = self._server_inbox.popleft()
        self.state = reduce_server_message(self.state, message)
        revision = get_game_message_revision(message)
        if revision is not None:
            self.state = replace(self.state, applied_game_revision=revision)
        return message, True

    def apply_action(self, action: UiAction) -> CoreActionResult:
        result = apply_ui_action(self.state, action)
        self.state = result.state
        return result

    @staticmethod
    def _is_immediate_server_message(message: ServerToClientMessage) -> bool:
        return isinstance(message, (SessionEnded, ServerError))
