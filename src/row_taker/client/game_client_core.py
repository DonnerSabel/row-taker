from __future__ import annotations

from collections import deque
from dataclasses import replace

from row_taker.cli.state_models import CliState, initial_cli_state
from row_taker.client.actions import UiAction
from row_taker.client.core_reducer import apply_ui_action, reduce_server_message
from row_taker.client.update import CoreUpdate
from row_taker.protocol.messages import ServerError, ServerToClientMessage, SessionEnded, get_game_message_revision


class GameClientCore:
    def __init__(self, state: CliState | None = None) -> None:
        self.state = initial_cli_state() if state is None else state
        self._server_inbox: deque[ServerToClientMessage] = deque()

    @property
    def server_inbox(self) -> tuple[ServerToClientMessage, ...]:
        return tuple(self._server_inbox)

    def on_server_message(self, message: ServerToClientMessage) -> CoreUpdate:
        self._server_inbox.append(message)
        revision = get_game_message_revision(message)
        if revision is not None:
            self.state = replace(self.state, received_game_revision=revision)
        return self._drain_server_inbox()

    def on_ui_action(self, action: UiAction) -> CoreUpdate:
        result = apply_ui_action(self.state, action)
        self.state = result.state
        first = CoreUpdate(
            state=self.state,
            outbound_messages=(result.outbound_message,) if result.outbound_message is not None else (),
            local_messages=(result.local_message,) if result.local_message is not None else (),
        )
        second = self._drain_server_inbox()
        return CoreUpdate(
            state=second.state,
            applied_server_messages=first.applied_server_messages + second.applied_server_messages,
            outbound_messages=first.outbound_messages + second.outbound_messages,
            local_messages=first.local_messages + second.local_messages,
        )

    def on_transport_closed(self, message: str) -> CoreUpdate:
        self.state = replace(self.state, session_error=message, exit_on_ack=False)
        return CoreUpdate(state=self.state)

    def has_pending_presentation(self) -> bool:
        return bool(self.state.pending_presentation_events)

    def _drain_server_inbox(self) -> CoreUpdate:
        applied: list[ServerToClientMessage] = []
        while self._server_inbox:
            next_message = self._server_inbox[0]
            if self._should_defer(next_message):
                break
            message = self._server_inbox.popleft()
            self.state = reduce_server_message(self.state, message)
            revision = get_game_message_revision(message)
            if revision is not None:
                self.state = replace(self.state, applied_game_revision=revision)
            applied.append(message)
        return CoreUpdate(state=self.state, applied_server_messages=tuple(applied))

    def _should_defer(self, message: ServerToClientMessage) -> bool:
        if not self.state.pending_presentation_events:
            return False
        return not isinstance(message, (SessionEnded, ServerError))
