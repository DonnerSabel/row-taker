from __future__ import annotations

from dataclasses import dataclass

from row_taker.client.actions import (
    ClientAction,
    ClientActionAdvancePresentation,
    ClientActionAssignSelfToSeat,
    ClientActionChooseCard,
    ClientActionChooseRow,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionLeaveSession,
    ClientActionRename,
    ClientActionStartGame,
)
from row_taker.client.core_state import PendingAction
from row_taker.client.state import (
    ClientState,
    UiMessage,
    advance_presentation_queue,
    append_pending_presentation_steps,
    apply_public_state,
    assign_identity,
    clear_flash_message,
    enter_game_mode,
    enter_lobby_submenu,
    mark_server_error,
    mark_session_ended,
    prepare_game_start,
    record_revealed_trick,
    request_card_choice,
    request_exit,
    request_row_choice,
    set_flash_message,
    set_trick_presentation_state,
    update_lobby_view,
)
from row_taker.client.trick_presentation_resolver import (
    apply_trick_row_choice,
    start_trick_presentation,
)
from row_taker.engine.game.player_state_ops import validate_submit_card, validate_submit_row_choice
from row_taker.protocol.messages import (
    AssignSeatToClient,
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameStarting,
    IdentityAssigned,
    LeaveSession,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    RowChoiceCommitted,
    ServerError,
    ServerToClientMessage,
    SessionEnded,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
)


@dataclass(frozen=True, slots=True)
class ActionResult:
    state: ClientState
    outbound_message: ClientToServerMessage | None = None
    local_message: str | None = None


def reduce_server_message(state: ClientState, message: ServerToClientMessage) -> ClientState:
    match message:
        case IdentityAssigned(client_id=client_id):
            return assign_identity(state, client_id)
        case LobbyStateUpdated(lobby=lobby):
            return update_lobby_view(state, lobby)
        case LobbyActionRejected(message=text):
            return set_flash_message(state, UiMessage(level="error", text=text))
        case GameStarting(lobby=lobby):
            next_state = prepare_game_start(state, lobby)
            return set_flash_message(next_state, UiMessage(level="info", text="Spielstart..."))
        case StateUpdated(state=public_state):
            next_presentation_state = state.trick_presentation_state
            if next_presentation_state is not None and next_presentation_state.pending_row_choice is None:
                next_presentation_state = None
            return apply_public_state(
                state,
                public_state,
                trick_presentation_state=next_presentation_state,
            )
        case CardsRevealed() as revealed:
            presentation_state = None
            queued_steps = ()
            if state.public_state is not None:
                presentation_state = start_trick_presentation(state.public_state, revealed)
                queued_steps = presentation_state.presentation_steps
            next_state = record_revealed_trick(
                state,
                revealed,
                trick_presentation_state=presentation_state,
            )
            next_state = clear_flash_message(next_state)
            return append_pending_presentation_steps(next_state, queued_steps)
        case RowChoiceCommitted(row_id=row_id):
            presentation_state = state.trick_presentation_state
            new_steps = ()
            if presentation_state is not None and presentation_state.pending_row_choice is not None:
                previous_count = len(presentation_state.presentation_steps)
                presentation_state = apply_trick_row_choice(presentation_state, row_id)
                new_steps = presentation_state.presentation_steps[previous_count:]
            next_state = enter_game_mode(state, pending_action=PendingAction.NONE)
            next_state = set_trick_presentation_state(next_state, presentation_state)
            next_state = clear_flash_message(next_state)
            return append_pending_presentation_steps(next_state, new_steps)
        case ChooseCardRequested(player_id=player_id, state=player_state):
            next_state = request_card_choice(state, player_id, player_state)
            return clear_flash_message(next_state)
        case ChooseRowRequested(player_id=player_id, state=player_state):
            next_state = request_row_choice(state, player_id, player_state)
            return clear_flash_message(next_state)
        case SessionEnded(message=text):
            return mark_session_ended(state, text)
        case ServerError(message=text):
            return mark_server_error(state, text)
        case _:
            raise TypeError(f"unsupported server message type: {type(message)!r}")


def apply_ui_action(state: ClientState, action: ClientAction) -> ActionResult:
    match action:
        case ClientActionLeaveSession():
            return ActionResult(
                state=request_exit(state, suppress_final_result=True),
                outbound_message=LeaveSession(),
            )
        case ClientActionAdvancePresentation():
            return ActionResult(state=advance_presentation_queue(state))
        case ClientActionRename(name=name):
            next_state = clear_flash_message(enter_lobby_submenu(state, "main"))
            return ActionResult(
                state=next_state,
                outbound_message=SetDisplayName(display_name=name),
            )
        case ClientActionAssignSelfToSeat(seat_index=seat_index):
            if state.own_client_id is None:
                return ActionResult(state=state, local_message="Eigene client_id unbekannt.")
            next_state = clear_flash_message(enter_lobby_submenu(state, "main"))
            return ActionResult(
                state=next_state,
                outbound_message=AssignSeatToClient(
                    seat_index=seat_index,
                    target_client_id=state.own_client_id,
                ),
            )
        case ClientActionCreateBot(seat_index=seat_index, name=name):
            next_state = clear_flash_message(enter_lobby_submenu(state, "main"))
            return ActionResult(
                state=next_state,
                outbound_message=CreateLocalBotOnSeat(
                    seat_index=seat_index,
                    display_name=name,
                ),
            )
        case ClientActionClearSeat(seat_index=seat_index):
            next_state = clear_flash_message(enter_lobby_submenu(state, "main"))
            return ActionResult(
                state=next_state,
                outbound_message=ClearSeat(seat_index=seat_index),
            )
        case ClientActionStartGame():
            next_state = clear_flash_message(enter_lobby_submenu(state, "main"))
            return ActionResult(
                state=next_state,
                outbound_message=RequestStartGame(),
            )
        case ClientActionChooseCard(card_value=value):
            player_state = state.player_state if state.pending_action == PendingAction.CHOOSE_CARD else None
            if player_state is None:
                return ActionResult(state=state, local_message="Keine Kartenauswahl aktiv.")
            try:
                validate_submit_card(player_state, value)
            except Exception as exc:
                return ActionResult(state=state, local_message=str(exc))
            next_state = enter_game_mode(
                state,
                pending_action=PendingAction.NONE,
                player_state=player_state,
            )
            next_state = clear_flash_message(next_state)
            return ActionResult(
                state=next_state,
                outbound_message=SubmitCard(card_value=value),
            )
        case ClientActionChooseRow(row_id=row_id):
            player_state = state.player_state if state.pending_action == PendingAction.CHOOSE_ROW else None
            if player_state is None:
                return ActionResult(state=state, local_message="Keine Reihenwahl aktiv.")
            try:
                validate_submit_row_choice(player_state, row_id)
            except Exception as exc:
                return ActionResult(state=state, local_message=str(exc))
            next_state = enter_game_mode(
                state,
                pending_action=PendingAction.NONE,
                player_state=player_state,
            )
            next_state = clear_flash_message(next_state)
            return ActionResult(
                state=next_state,
                outbound_message=SubmitRowChoice(row_id=row_id),
            )
        case _:
            raise TypeError(f"unsupported client action type: {type(action)!r}")
