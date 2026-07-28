from __future__ import annotations

from row_taker.client.action_transitions import (
    ActionResult,
    advance_presentation,
    assign_self_to_seat,
    clear_seat,
    create_bot,
    leave_session,
    rename_player,
    request_game_start,
    submit_card,
    submit_row_choice,
)
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
from row_taker.client.server_transitions import (
    commit_row_choice,
    end_session,
    receive_identity,
    receive_lobby_state,
    reject_lobby_action,
    report_server_error,
    request_card,
    request_row,
    reveal_cards,
    start_game,
    update_public_game_state,
)
from row_taker.client.state import ClientState
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


def reduce_server_message(state: ClientState, message: ServerToClientMessage) -> ClientState:
    match message:
        case IdentityAssigned():
            return receive_identity(state, message)
        case LobbyStateUpdated():
            return receive_lobby_state(state, message)
        case LobbyActionRejected():
            return reject_lobby_action(state, message)
        case GameStarting():
            return start_game(state, message)
        case StateUpdated():
            return update_public_game_state(state, message)
        case CardsRevealed():
            return reveal_cards(state, message)
        case RowChoiceCommitted():
            return commit_row_choice(state, message)
        case ChooseCardRequested():
            return request_card(state, message)
        case ChooseRowRequested():
            return request_row(state, message)
        case SessionEnded():
            return end_session(state, message)
        case ServerError():
            return report_server_error(state, message)
        case _:
            raise TypeError(f"unsupported server message type: {type(message)!r}")


def apply_ui_action(state: ClientState, action: ClientAction) -> ActionResult:
    match action:
        case ClientActionLeaveSession():
            return leave_session(state)
        case ClientActionAdvancePresentation():
            return advance_presentation(state)
        case ClientActionRename():
            return rename_player(state, action)
        case ClientActionAssignSelfToSeat():
            return assign_self_to_seat(state, action)
        case ClientActionCreateBot():
            return create_bot(state, action)
        case ClientActionClearSeat():
            return clear_seat(state, action)
        case ClientActionStartGame():
            return request_game_start(state)
        case ClientActionChooseCard():
            return submit_card(state, action)
        case ClientActionChooseRow():
            return submit_row_choice(state, action)
        case _:
            raise TypeError(f"unsupported client action type: {type(action)!r}")
