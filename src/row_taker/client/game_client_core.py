from __future__ import annotations

from collections import deque
from dataclasses import replace

from row_taker.client.actions import UiAction
from row_taker.client.core_reducer import apply_ui_action, reduce_server_message
from row_taker.client.core_state import ClientCoreState, initial_client_core_state
from row_taker.client.update import (
    CoreEffect,
    CoreUpdate,
    EffectPendingActionChanged,
    EffectPresentationAdvanced,
    EffectPresentationQueued,
    EffectSessionEnded,
    EffectStateChanged,
)
from row_taker.protocol.messages import ServerError, ServerToClientMessage, SessionEnded, get_game_message_revision


class GameClientCore:
    """GUI-neutral client core.

    This is the canonical client pipeline.
    """

    def __init__(self, state: ClientCoreState | None = None) -> None:
        self.state = initial_client_core_state() if state is None else state
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
        previous_state = self.state
        action_result = apply_ui_action(self.state, action)
        self.state = action_result.state

        first_update = self._build_update(
            previous_state=previous_state,
            next_state=self.state,
            applied_server_messages=(),
            outbound_messages=(action_result.outbound_message,) if action_result.outbound_message is not None else (),
            local_messages=(action_result.local_message,) if action_result.local_message is not None else (),
        )

        second_update = self._drain_server_inbox()
        return self._merge_updates(first_update, second_update)

    def on_transport_closed(self, message: str) -> CoreUpdate:
        previous_state = self.state
        self.state = replace(self.state, session_error=message)
        return self._build_update(
            previous_state=previous_state,
            next_state=self.state,
            applied_server_messages=(),
            outbound_messages=(),
            local_messages=(),
        )

    def has_pending_presentation(self) -> bool:
        return bool(self.state.pending_presentation_events)

    def _drain_server_inbox(self) -> CoreUpdate:
        update = CoreUpdate(state=self.state)

        while self._server_inbox:
            next_message = self._server_inbox[0]
            if self._should_defer_server_message_application(next_message):
                return update

            message = self._server_inbox.popleft()
            previous_state = self.state
            self.state = reduce_server_message(self.state, message)

            revision = get_game_message_revision(message)
            if revision is not None:
                self.state = replace(self.state, applied_game_revision=revision)

            next_update = self._build_update(
                previous_state=previous_state,
                next_state=self.state,
                applied_server_messages=(message,),
                outbound_messages=(),
                local_messages=(),
            )
            update = self._merge_updates(update, next_update)

        return update

    def _should_defer_server_message_application(self, message: ServerToClientMessage) -> bool:
        if not self.state.pending_presentation_events:
            return False
        return not isinstance(message, (SessionEnded, ServerError))

    def _build_update(
        self,
        *,
        previous_state: ClientCoreState,
        next_state: ClientCoreState,
        applied_server_messages: tuple[ServerToClientMessage, ...],
        outbound_messages,
        local_messages,
    ) -> CoreUpdate:
        return CoreUpdate(
            state=next_state,
            applied_server_messages=applied_server_messages,
            outbound_messages=tuple(outbound_messages),
            local_messages=tuple(local_messages),
            effects=self._derive_effects(previous_state, next_state),
        )

    def _derive_effects(
        self,
        previous_state: ClientCoreState,
        next_state: ClientCoreState,
    ) -> tuple[CoreEffect, ...]:
        effects: list[CoreEffect] = []

        if next_state != previous_state:
            effects.append(EffectStateChanged())

        queued_delta = len(next_state.pending_presentation_events) - len(previous_state.pending_presentation_events)
        if queued_delta > 0:
            effects.append(EffectPresentationQueued(queued_delta))

        if len(next_state.presentation_events) > len(previous_state.presentation_events):
            effects.append(EffectPresentationAdvanced(next_state.presentation_events[-1]))

        if next_state.pending_action != previous_state.pending_action:
            effects.append(EffectPendingActionChanged(next_state.pending_action))

        if next_state.session_error is not None and next_state.session_error != previous_state.session_error:
            effects.append(EffectSessionEnded(next_state.session_error))

        return tuple(effects)

    @staticmethod
    def _merge_updates(first: CoreUpdate, second: CoreUpdate) -> CoreUpdate:
        return CoreUpdate(
            state=second.state,
            applied_server_messages=first.applied_server_messages + second.applied_server_messages,
            outbound_messages=first.outbound_messages + second.outbound_messages,
            local_messages=first.local_messages + second.local_messages,
            effects=first.effects + second.effects,
        )
