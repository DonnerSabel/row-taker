from __future__ import annotations

from dataclasses import replace

from row_taker.client.core_state import ClientCoreState, ClientMode, PendingAction
from row_taker.client.presentation_events import PresentationEvent
from row_taker.client.trick_presentation_resolver import apply_trick_row_choice, start_trick_presentation
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
    ServerToClientMessage,
    SessionEnded,
    StateUpdated,
)


def append_presentation_events(
    state: ClientCoreState,
    events: tuple[PresentationEvent, ...],
) -> ClientCoreState:
    if not events:
        return state
    return replace(state, pending_presentation_events=state.pending_presentation_events + events)


def reset_presentation_queue(state: ClientCoreState) -> ClientCoreState:
    return replace(state, presentation_events=(), pending_presentation_events=())


def advance_presentation_queue(state: ClientCoreState) -> ClientCoreState:
    if not state.pending_presentation_events:
        return state
    next_event = state.pending_presentation_events[0]
    return replace(
        state,
        presentation_events=state.presentation_events + (next_event,),
        pending_presentation_events=state.pending_presentation_events[1:],
    )


def reduce_server_message(state: ClientCoreState, message: ServerToClientMessage) -> ClientCoreState:
    match message:
        case IdentityAssigned(client_id=client_id):
            return replace(state, own_client_id=client_id)
        case LobbyStateUpdated(lobby=lobby):
            return replace(state, lobby_view=lobby)
        case LobbyActionRejected():
            return state
        case GameStarting(lobby=lobby):
            return replace(
                state,
                lobby_view=lobby,
                public_state=None,
                revealed_trick=None,
                trick_presentation_state=None,
                presentation_events=(),
                pending_presentation_events=(),
                client_mode=ClientMode.GAME,
                pending_action=PendingAction.NONE,
            )
        case StateUpdated(state=public_state):
            next_trick_presentation_state = state.trick_presentation_state
            if next_trick_presentation_state is not None and next_trick_presentation_state.pending_row_choice is None:
                next_trick_presentation_state = None
            return replace(
                state,
                public_state=public_state,
                revealed_trick=None,
                trick_presentation_state=next_trick_presentation_state,
                client_mode=ClientMode.GAME,
                pending_action=PendingAction.NONE,
            )
        case CardsRevealed() as revealed:
            trick_presentation_state = None
            queued_events: tuple[PresentationEvent, ...] = ()
            if state.public_state is not None:
                trick_presentation_state = start_trick_presentation(state.public_state, revealed)
                queued_events = trick_presentation_state.events
            next_state = replace(
                state,
                revealed_trick=revealed,
                trick_presentation_state=trick_presentation_state,
            )
            return append_presentation_events(next_state, queued_events)
        case RowChoiceCommitted(row_id=row_id):
            trick_presentation_state = state.trick_presentation_state
            newly_queued_events: tuple[PresentationEvent, ...] = ()
            if trick_presentation_state is not None and trick_presentation_state.pending_row_choice is not None:
                previous_count = len(trick_presentation_state.events)
                trick_presentation_state = apply_trick_row_choice(trick_presentation_state, row_id)
                newly_queued_events = trick_presentation_state.events[previous_count:]
            next_state = replace(
                state,
                trick_presentation_state=trick_presentation_state,
                pending_action=PendingAction.NONE,
            )
            return append_presentation_events(next_state, newly_queued_events)
        case ChooseCardRequested(player_id=player_id, state=_player_state):
            return replace(
                state,
                own_player_id=player_id,
                revealed_trick=None,
                trick_presentation_state=None,
                presentation_events=(),
                pending_presentation_events=(),
                client_mode=ClientMode.GAME,
                pending_action=PendingAction.CHOOSE_CARD,
            )
        case ChooseRowRequested(player_id=player_id, state=_player_state):
            return replace(
                state,
                own_player_id=player_id,
                client_mode=ClientMode.GAME,
                pending_action=PendingAction.CHOOSE_ROW,
            )
        case SessionEnded(message=text):
            return replace(
                state,
                session_error=text,
                client_mode=ClientMode.ENDED,
                pending_action=PendingAction.NONE,
            )
        case ServerError(message=text):
            return replace(
                state,
                session_error=text,
            )
        case _:
            raise TypeError(f"unsupported server message type: {type(message)!r}")
