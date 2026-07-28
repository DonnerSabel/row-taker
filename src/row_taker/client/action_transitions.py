from __future__ import annotations

from dataclasses import dataclass

from row_taker.client.actions import (
    ClientActionAssignSelfToSeat,
    ClientActionChooseCard,
    ClientActionChooseRow,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionRename,
)
from row_taker.client.core_state import PendingAction
from row_taker.client.presentation_queue import advance_presentation_queue
from row_taker.client.state import (
    ClientState,
    clear_flash_message,
    enter_game_mode,
    enter_lobby_submenu,
    request_exit,
)
from row_taker.engine.game.player_state_ops import validate_submit_card, validate_submit_row_choice
from row_taker.protocol.messages import (
    AssignSeatToClient,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    LeaveSession,
    RequestStartGame,
    SetDisplayName,
    SubmitCard,
    SubmitRowChoice,
)


@dataclass(frozen=True, slots=True)
class ActionResult:
    state: ClientState
    outbound_message: ClientToServerMessage | None = None
    local_message: str | None = None


def leave_session(state: ClientState) -> ActionResult:
    return ActionResult(
        state=request_exit(state, suppress_final_result=True),
        outbound_message=LeaveSession(),
    )


def advance_presentation(state: ClientState) -> ActionResult:
    return ActionResult(state=advance_presentation_queue(state))


def _send_lobby_command(
    state: ClientState,
    message: ClientToServerMessage,
) -> ActionResult:
    next_state = clear_flash_message(enter_lobby_submenu(state, "main"))
    return ActionResult(state=next_state, outbound_message=message)


def rename_player(state: ClientState, action: ClientActionRename) -> ActionResult:
    return _send_lobby_command(state, SetDisplayName(display_name=action.name))


def assign_self_to_seat(
    state: ClientState,
    action: ClientActionAssignSelfToSeat,
) -> ActionResult:
    if state.own_client_id is None:
        return ActionResult(state=state, local_message="Eigene client_id unbekannt.")
    return _send_lobby_command(
        state,
        AssignSeatToClient(
            seat_index=action.seat_index,
            target_client_id=state.own_client_id,
        ),
    )


def create_bot(state: ClientState, action: ClientActionCreateBot) -> ActionResult:
    return _send_lobby_command(
        state,
        CreateLocalBotOnSeat(
            seat_index=action.seat_index,
            display_name=action.name,
        ),
    )


def clear_seat(state: ClientState, action: ClientActionClearSeat) -> ActionResult:
    return _send_lobby_command(state, ClearSeat(seat_index=action.seat_index))


def request_game_start(state: ClientState) -> ActionResult:
    return _send_lobby_command(state, RequestStartGame())


def submit_card(state: ClientState, action: ClientActionChooseCard) -> ActionResult:
    player_state = state.player_state if state.pending_action == PendingAction.CHOOSE_CARD else None
    if player_state is None:
        return ActionResult(state=state, local_message="Keine Kartenauswahl aktiv.")
    try:
        validate_submit_card(player_state, action.card_value)
    except ValueError as exc:
        return ActionResult(state=state, local_message=str(exc))
    next_state = enter_game_mode(
        state,
        pending_action=PendingAction.NONE,
        player_state=player_state,
    )
    next_state = clear_flash_message(next_state)
    return ActionResult(
        state=next_state,
        outbound_message=SubmitCard(card_value=action.card_value),
    )


def submit_row_choice(state: ClientState, action: ClientActionChooseRow) -> ActionResult:
    player_state = state.player_state if state.pending_action == PendingAction.CHOOSE_ROW else None
    if player_state is None:
        return ActionResult(state=state, local_message="Keine Reihenwahl aktiv.")
    try:
        validate_submit_row_choice(player_state, action.row_id)
    except ValueError as exc:
        return ActionResult(state=state, local_message=str(exc))
    next_state = enter_game_mode(
        state,
        pending_action=PendingAction.NONE,
        player_state=player_state,
    )
    next_state = clear_flash_message(next_state)
    return ActionResult(
        state=next_state,
        outbound_message=SubmitRowChoice(row_id=action.row_id),
    )
