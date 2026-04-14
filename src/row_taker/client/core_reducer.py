from __future__ import annotations

from dataclasses import dataclass

from row_taker.client.trick_presentation_resolver import apply_trick_row_choice, start_trick_presentation
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
from row_taker.client.core_state import ClientMode, PendingAction
from row_taker.client.presentation_events import PresentationEvent
from row_taker.client.state import (
    ClientState,
    UiMessage,
    enter_game_mode,
    enter_lobby_submenu,
    with_core_updates,
    with_feedback_updates,
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



def append_presentation_events(state: ClientState, events: tuple[PresentationEvent, ...]) -> ClientState:
    if not events:
        return state
    return with_core_updates(
        state,
        pending_presentation_events=state.pending_presentation_events + events,
    )



def advance_presentation_queue(state: ClientState) -> ClientState:
    if not state.pending_presentation_events:
        return state
    next_event = state.pending_presentation_events[0]
    return with_core_updates(
        state,
        presentation_events=state.presentation_events + (next_event,),
        pending_presentation_events=state.pending_presentation_events[1:],
    )



def reduce_server_message(state: ClientState, message: ServerToClientMessage) -> ClientState:
    match message:
        case IdentityAssigned(client_id=client_id):
            return with_core_updates(state, own_client_id=client_id)
        case LobbyStateUpdated(lobby=lobby):
            return with_core_updates(state, lobby_view=lobby)
        case LobbyActionRejected(message=text):
            return with_feedback_updates(state, flash_message=UiMessage(level="error", text=text))
        case GameStarting(lobby=lobby):
            next_state = enter_game_mode(state, pending_action=PendingAction.NONE)
            next_state = with_core_updates(
                next_state,
                lobby_view=lobby,
                public_state=None,
                player_state=None,
                revealed_trick=None,
                trick_presentation_state=None,
                presentation_events=(),
                pending_presentation_events=(),
            )
            return with_feedback_updates(next_state, flash_message=UiMessage(level="info", text="Spielstart..."))
        case StateUpdated(state=public_state):
            next_state = state
            if next_state.pending_action == PendingAction.CHOOSE_ROW:
                next_state = enter_game_mode(next_state, pending_action=PendingAction.NONE)
            next_presentation_state = next_state.trick_presentation_state
            if next_presentation_state is not None and next_presentation_state.pending_row_choice is None:
                next_presentation_state = None
            return with_core_updates(
                next_state,
                public_state=public_state,
                revealed_trick=None,
                trick_presentation_state=next_presentation_state,
            )
        case CardsRevealed() as revealed:
            presentation_state = None
            queued_events: tuple[PresentationEvent, ...] = ()
            if state.public_state is not None:
                presentation_state = start_trick_presentation(state.public_state, revealed)
                queued_events = presentation_state.events
            next_state = with_core_updates(
                state,
                revealed_trick=revealed,
                trick_presentation_state=presentation_state,
            )
            next_state = with_feedback_updates(next_state, flash_message=None)
            return append_presentation_events(next_state, queued_events)
        case RowChoiceCommitted(row_id=row_id):
            presentation_state = state.trick_presentation_state
            new_events: tuple[PresentationEvent, ...] = ()
            if presentation_state is not None and presentation_state.pending_row_choice is not None:
                previous_count = len(presentation_state.events)
                presentation_state = apply_trick_row_choice(presentation_state, row_id)
                new_events = presentation_state.events[previous_count:]
            next_state = enter_game_mode(state, pending_action=PendingAction.NONE)
            next_state = with_core_updates(next_state, trick_presentation_state=presentation_state)
            next_state = with_feedback_updates(next_state, flash_message=None)
            return append_presentation_events(next_state, new_events)
        case ChooseCardRequested(player_id=player_id, state=player_state):
            next_state = enter_game_mode(state, pending_action=PendingAction.CHOOSE_CARD, player_state=player_state)
            next_state = with_core_updates(
                next_state,
                own_player_id=player_id,
                public_state=player_state.public_state,
                player_state=player_state,
                revealed_trick=None,
                trick_presentation_state=None,
                presentation_events=(),
                pending_presentation_events=(),
                client_mode=ClientMode.GAME,
                pending_action=PendingAction.CHOOSE_CARD,
            )
            return with_feedback_updates(next_state, flash_message=None)
        case ChooseRowRequested(player_id=player_id, state=player_state):
            next_state = enter_game_mode(state, pending_action=PendingAction.CHOOSE_ROW, player_state=player_state)
            next_state = with_core_updates(
                next_state,
                own_player_id=player_id,
                public_state=player_state.public_state,
                player_state=player_state,
                client_mode=ClientMode.GAME,
                pending_action=PendingAction.CHOOSE_ROW,
            )
            return with_feedback_updates(next_state, flash_message=None)
        case SessionEnded(message=text):
            next_state = with_core_updates(state, session_error=text)
            return with_feedback_updates(
                next_state,
                exit_on_ack=False,
                suppress_final_result=True,
                should_exit=True,
                flash_message=None,
            )
        case ServerError(message=text):
            next_state = with_core_updates(state, session_error=text)
            return with_feedback_updates(
                next_state,
                exit_on_ack=True,
                suppress_final_result=True,
                flash_message=None,
            )
        case _:
            raise TypeError(f"unsupported server message type: {type(message)!r}")



def apply_ui_action(state: ClientState, action: ClientAction) -> ActionResult:
    match action:
        case ClientActionLeaveSession():
            return ActionResult(
                state=with_feedback_updates(state, should_exit=True, suppress_final_result=True),
                outbound_message=LeaveSession(),
            )
        case ClientActionAdvancePresentation():
            return ActionResult(state=advance_presentation_queue(state))
        case ClientActionRename(name=name):
            next_state = enter_lobby_submenu(state, "main")
            next_state = with_feedback_updates(next_state, flash_message=None)
            return ActionResult(
                state=next_state,
                outbound_message=SetDisplayName(display_name=name),
            )
        case ClientActionAssignSelfToSeat(seat_index=seat_index):
            if state.own_client_id is None:
                return ActionResult(state=state, local_message="Eigene client_id unbekannt.")
            next_state = enter_lobby_submenu(state, "main")
            next_state = with_feedback_updates(next_state, flash_message=None)
            return ActionResult(
                state=next_state,
                outbound_message=AssignSeatToClient(seat_index=seat_index, target_client_id=state.own_client_id),
            )
        case ClientActionCreateBot(seat_index=seat_index, name=name):
            next_state = enter_lobby_submenu(state, "main")
            next_state = with_feedback_updates(next_state, flash_message=None)
            return ActionResult(
                state=next_state,
                outbound_message=CreateLocalBotOnSeat(seat_index=seat_index, display_name=name),
            )
        case ClientActionClearSeat(seat_index=seat_index):
            next_state = enter_lobby_submenu(state, "main")
            next_state = with_feedback_updates(next_state, flash_message=None)
            return ActionResult(
                state=next_state,
                outbound_message=ClearSeat(seat_index=seat_index),
            )
        case ClientActionStartGame():
            next_state = enter_lobby_submenu(state, "main")
            next_state = with_feedback_updates(next_state, flash_message=None)
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
            next_state = enter_game_mode(state, pending_action=PendingAction.NONE, player_state=player_state)
            next_state = with_feedback_updates(next_state, flash_message=None)
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
            next_state = enter_game_mode(state, pending_action=PendingAction.NONE, player_state=player_state)
            next_state = with_feedback_updates(next_state, flash_message=None)
            return ActionResult(
                state=next_state,
                outbound_message=SubmitRowChoice(row_id=row_id),
            )
        case _:
            raise TypeError(f"unsupported client action type: {type(action)!r}")
