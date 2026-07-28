from __future__ import annotations

from row_taker.client.core_state import PendingAction
from row_taker.client.presentation_queue import append_pending_presentation_steps
from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.state import (
    ClientState,
    UiMessage,
    apply_public_state,
    assign_identity,
    clear_flash_message,
    enter_game_mode,
    mark_server_error,
    mark_session_ended,
    prepare_game_start,
    record_revealed_trick,
    request_card_choice,
    request_row_choice,
    set_flash_message,
    set_trick_presentation_state,
    update_lobby_view,
)
from row_taker.client.trick_presentation_resolver import (
    apply_trick_row_choice,
    start_trick_presentation,
)
from row_taker.protocol.messages import (
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    GameStarting,
    IdentityAssigned,
    LobbyActionRejected,
    LobbyStateUpdated,
    RowChoiceCommitted,
    ServerError,
    SessionEnded,
    StateUpdated,
)


def receive_identity(state: ClientState, message: IdentityAssigned) -> ClientState:
    return assign_identity(state, message.client_id)


def receive_lobby_state(state: ClientState, message: LobbyStateUpdated) -> ClientState:
    return update_lobby_view(state, message.lobby)


def reject_lobby_action(state: ClientState, message: LobbyActionRejected) -> ClientState:
    return set_flash_message(state, UiMessage(level="error", text=message.message))


def start_game(state: ClientState, message: GameStarting) -> ClientState:
    next_state = prepare_game_start(state, message.lobby)
    return set_flash_message(next_state, UiMessage(level="info", text="Spielstart..."))


def update_public_game_state(state: ClientState, message: StateUpdated) -> ClientState:
    next_presentation_state = state.trick_presentation_state
    if next_presentation_state is not None and next_presentation_state.pending_row_choice is None:
        next_presentation_state = None
    return apply_public_state(
        state,
        message.state,
        trick_presentation_state=next_presentation_state,
    )


def reveal_cards(state: ClientState, message: CardsRevealed) -> ClientState:
    presentation_state = None
    queued_steps: tuple[PresentationStep, ...] = ()
    if state.public_state is not None:
        presentation_state = start_trick_presentation(state.public_state, message)
        queued_steps = presentation_state.presentation_steps
    next_state = record_revealed_trick(
        state,
        message,
        trick_presentation_state=presentation_state,
    )
    next_state = clear_flash_message(next_state)
    return append_pending_presentation_steps(next_state, queued_steps)


def commit_row_choice(state: ClientState, message: RowChoiceCommitted) -> ClientState:
    presentation_state = state.trick_presentation_state
    new_steps: tuple[PresentationStep, ...] = ()
    if presentation_state is not None and presentation_state.pending_row_choice is not None:
        previous_count = len(presentation_state.presentation_steps)
        presentation_state = apply_trick_row_choice(presentation_state, message.row_id)
        new_steps = presentation_state.presentation_steps[previous_count:]
    next_state = enter_game_mode(state, pending_action=PendingAction.NONE)
    next_state = set_trick_presentation_state(next_state, presentation_state)
    next_state = clear_flash_message(next_state)
    return append_pending_presentation_steps(next_state, new_steps)


def request_card(state: ClientState, message: ChooseCardRequested) -> ClientState:
    next_state = request_card_choice(state, message.player_id, message.state)
    return clear_flash_message(next_state)


def request_row(state: ClientState, message: ChooseRowRequested) -> ClientState:
    next_state = request_row_choice(state, message.player_id, message.state)
    return clear_flash_message(next_state)


def end_session(state: ClientState, message: SessionEnded) -> ClientState:
    return mark_session_ended(state, message.message)


def report_server_error(state: ClientState, message: ServerError) -> ClientState:
    return mark_server_error(state, message.message)
