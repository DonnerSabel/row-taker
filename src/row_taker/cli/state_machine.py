from __future__ import annotations

import logging

from row_taker.cli.frontend import (
    clear_flash,
    mark_server_error,
    mark_session_ended,
    parse_text_to_action,
    set_flash,
    sync_frontend_to_core,
)
from row_taker.cli.state_models import CliState, apply_client_core_state
from row_taker.client.core_reducer import apply_ui_action
from row_taker.client.core_state import PendingAction
from row_taker.protocol.messages import LobbyActionRejected, ServerError, ServerToClientMessage, SessionEnded

logger = logging.getLogger("row_taker.cli.state_machine")


class UserInputResult:
    def __init__(self, state: CliState, outbound_message=None) -> None:
        self.state = state
        self.outbound_message = outbound_message



def append_presentation_events(state: CliState, events):
    raise NotImplementedError("presentation queue is handled by GameClientCore")



def reset_presentation_queue(state: CliState) -> CliState:
    from row_taker.client.core_reducer import reset_presentation_queue as reset_core_presentation_queue

    return apply_client_core_state(state, reset_core_presentation_queue(state.core_state))



def advance_presentation_queue(state: CliState) -> CliState:
    from row_taker.client.actions import UiActionAdvancePresentation

    result = apply_ui_action(state.core_state, UiActionAdvancePresentation())
    return apply_client_core_state(state, result.state)



def reduce_server_message(state: CliState, message: ServerToClientMessage) -> CliState:
    from row_taker.client.core_reducer import reduce_server_message as reduce_core_server_message

    state = apply_client_core_state(state, reduce_core_server_message(state.core_state, message))
    state = sync_frontend_to_core(state)
    match message:
        case LobbyActionRejected(message=text):
            return set_flash(state, "error", text)
        case SessionEnded():
            logger.debug("session ended applied: message=%r", state.session_error)
            return mark_session_ended(state)
        case ServerError():
            return mark_server_error(state)
        case _:
            return state



def reduce_user_input(state: CliState, text: str) -> UserInputResult:
    original_state = state
    parsed = parse_text_to_action(state, text)
    state = parsed.state
    if parsed.action is None:
        return UserInputResult(state=state)

    result = apply_ui_action(state.core_state, parsed.action)
    state = apply_client_core_state(state, result.state)
    state = sync_frontend_to_core(state)
    if result.local_message is not None:
        state = apply_client_core_state(original_state, result.state)
        state = set_flash(state, "error", result.local_message)
        return UserInputResult(state=state)
    return UserInputResult(state=clear_flash(state), outbound_message=result.outbound_message)
