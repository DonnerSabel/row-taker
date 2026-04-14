from __future__ import annotations

import logging

from row_taker.cli.frontend import CliFrontend, mark_server_error, mark_session_ended, set_flash
from row_taker.cli.state_models import CliState, apply_client_core_state
from row_taker.client.game_client_core import GameClientCore
from row_taker.protocol.messages import LobbyActionRejected, ServerError, ServerToClientMessage, SessionEnded

logger = logging.getLogger("row_taker.cli.state_machine")


class UserInputResult:
    def __init__(self, state: CliState, outbound_message=None) -> None:
        self.state = state
        self.outbound_message = outbound_message


_FRONTEND = CliFrontend()


def append_presentation_events(state: CliState, events):
    raise NotImplementedError("presentation queue is handled by GameClientCore")


def reset_presentation_queue(state: CliState) -> CliState:
    from row_taker.client.core_reducer import reset_presentation_queue as reset_core_presentation_queue

    return apply_client_core_state(state, reset_core_presentation_queue(state.core_state))


def advance_presentation_queue(state: CliState) -> CliState:
    from row_taker.client.actions import UiActionAdvancePresentation

    core = GameClientCore(state.core_state)
    core.apply_action(UiActionAdvancePresentation())

    while True:
        flowed = core.continue_ready_flow()
        if not flowed.applied_server_messages:
            state = apply_client_core_state(state, core.state)
            return _FRONTEND.sync_to_core(state)


def reduce_server_message(state: CliState, message: ServerToClientMessage) -> CliState:
    core = GameClientCore(state.core_state)
    update = core.receive_server_message(message)

    state = apply_client_core_state(state, update.state)
    state = _FRONTEND.sync_to_core(state)

    for applied in update.applied_server_messages:
        match applied:
            case LobbyActionRejected(message=text):
                state = set_flash(state, "error", text)
            case SessionEnded():
                logger.debug("session ended applied: message=%r", state.session_error)
                state = mark_session_ended(state)
            case ServerError():
                state = mark_server_error(state)
            case _:
                pass

    return state


def reduce_user_input(state: CliState, text: str) -> UserInputResult:
    parsed = _FRONTEND.handle_text_input(state, text)
    state = parsed.state

    if parsed.action is None:
        return UserInputResult(state=state)

    core = GameClientCore(state.core_state)
    update = core.apply_action(parsed.action)

    state = apply_client_core_state(state, core.state)
    state = _FRONTEND.sync_to_core(state)

    if update.local_messages:
        return UserInputResult(state=set_flash(state, "error", update.local_messages[-1]))

    while True:
        flowed = core.continue_ready_flow()
        if not flowed.applied_server_messages:
            state = apply_client_core_state(state, core.state)
            state = _FRONTEND.sync_to_core(state)
            outbound = update.outbound_messages[0] if update.outbound_messages else None
            return UserInputResult(state=state, outbound_message=outbound)

        state = apply_client_core_state(state, core.state)
        state = _FRONTEND.sync_to_core(state)
