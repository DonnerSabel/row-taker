from __future__ import annotations

from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.state_mappers import (
    delta_public_state_from_dict,
    delta_public_state_to_dict,
    player_state_from_dict,
    player_state_to_dict,
    public_state_from_dict,
    public_state_to_dict,
)
from row_taker.protocol.messages import (
    AssignSeatToClient,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameStarting,
    IdentityAssigned,
    JoinLobby,
    LeaveSession,
    LobbyActionRejected,
    LobbyParticipantView,
    LobbySeatView,
    LobbyStateUpdated,
    LobbyView,
    PlayedCardView,
    RequestStartGame,
    SessionEnded,
    SessionEndReason,
    ServerError,
    ServerToClientMessage,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
    TrickRevealed,
)


def _lobby_participant_to_dict(participant: LobbyParticipantView) -> dict[str, object]:
    return {
        "client_id": participant.client_id,
        "display_name": participant.display_name,
        "participant_kind": participant.participant_kind,
        "seat_index": participant.seat_index,
        "endpoint": participant.endpoint,
    }


def _lobby_participant_from_dict(data: object) -> LobbyParticipantView:
    if not isinstance(data, dict):
        raise TypeError(f"lobby participant must be a dict, got {type(data)!r}")
    endpoint = data.get("endpoint")
    return LobbyParticipantView(
        client_id=str(data["client_id"]),
        display_name=str(data["display_name"]),
        participant_kind=str(data["participant_kind"]),
        seat_index=None if data.get("seat_index") is None else int(data["seat_index"]),
        endpoint=None if endpoint is None else str(endpoint),
    )


def _lobby_seat_to_dict(seat: LobbySeatView) -> dict[str, object]:
    return {
        "seat_index": seat.seat_index,
        "occupant_client_id": seat.occupant_client_id,
        "occupant_display_name": seat.occupant_display_name,
        "occupant_kind": seat.occupant_kind,
        "occupant_endpoint": seat.occupant_endpoint,
    }


def _lobby_seat_from_dict(data: object) -> LobbySeatView:
    if not isinstance(data, dict):
        raise TypeError(f"lobby seat must be a dict, got {type(data)!r}")
    occupant_endpoint = data.get("occupant_endpoint")
    return LobbySeatView(
        seat_index=int(data["seat_index"]),
        occupant_client_id=None if data.get("occupant_client_id") is None else str(data["occupant_client_id"]),
        occupant_display_name=None if data.get("occupant_display_name") is None else str(data["occupant_display_name"]),
        occupant_kind=None if data.get("occupant_kind") is None else str(data["occupant_kind"]),
        occupant_endpoint=None if occupant_endpoint is None else str(occupant_endpoint),
    )


def _lobby_view_to_dict(lobby: LobbyView) -> dict[str, object]:
    return {
        "seat_count": lobby.seat_count,
        "participants": [_lobby_participant_to_dict(participant) for participant in lobby.participants],
        "seats": [_lobby_seat_to_dict(seat) for seat in lobby.seats],
        "game_started": lobby.game_started,
        "server_endpoint": lobby.server_endpoint,
    }


def _lobby_view_from_dict(data: object) -> LobbyView:
    if not isinstance(data, dict):
        raise TypeError(f"lobby view data must be a dict, got {type(data)!r}")
    server_endpoint = data.get("server_endpoint")
    return LobbyView(
        seat_count=int(data["seat_count"]),
        participants=tuple(_lobby_participant_from_dict(participant) for participant in data["participants"]),
        seats=tuple(_lobby_seat_from_dict(seat) for seat in data["seats"]),
        game_started=bool(data["game_started"]),
        server_endpoint=None if server_endpoint is None else str(server_endpoint),
    )


def _played_card_to_dict(card: PlayedCardView) -> dict[str, object]:
    return {
        "player_id": str(card.player_id),
        "player_name": card.player_name,
        "card_value": card.card_value,
    }


def _played_card_from_dict(data: object) -> PlayedCardView:
    if not isinstance(data, dict):
        raise TypeError(f"played card must be a dict, got {type(data)!r}")
    return PlayedCardView(
        player_id=PlayerID(str(data["player_id"])),
        player_name=str(data["player_name"]),
        card_value=int(data["card_value"]),
    )


def client_message_to_dict(message: ClientToServerMessage) -> dict[str, object]:
    if isinstance(message, JoinLobby):
        return {"type": "join_lobby", "display_name": message.display_name, "requested_client_id": message.requested_client_id}
    if isinstance(message, SetDisplayName):
        return {"type": "set_display_name", "display_name": message.display_name}
    if isinstance(message, AssignSeatToClient):
        return {"type": "assign_seat_to_client", "seat_index": message.seat_index, "target_client_id": message.target_client_id}
    if isinstance(message, CreateLocalBotOnSeat):
        return {"type": "create_local_bot_on_seat", "seat_index": message.seat_index, "display_name": message.display_name}
    if isinstance(message, ClearSeat):
        return {"type": "clear_seat", "seat_index": message.seat_index}
    if isinstance(message, RequestStartGame):
        return {"type": "request_start_game"}
    if isinstance(message, LeaveSession):
        return {"type": "leave_session"}
    if isinstance(message, SubmitCard):
        return {"type": "submit_card", "player_id": str(message.player_id), "card_value": message.card_value}
    if isinstance(message, SubmitRowChoice):
        return {"type": "submit_row_choice", "player_id": str(message.player_id), "row_id": str(message.row_id)}
    raise TypeError(f"unsupported client message type: {type(message)!r}")


def client_message_from_dict(data: dict[str, object]) -> ClientToServerMessage:
    message_type = str(data["type"])
    if message_type == "join_lobby":
        requested = data.get("requested_client_id")
        requested_client_id = None if requested is None else str(requested)
        return JoinLobby(display_name=str(data["display_name"]), requested_client_id=requested_client_id)
    if message_type == "set_display_name":
        return SetDisplayName(display_name=str(data["display_name"]))
    if message_type == "assign_seat_to_client":
        return AssignSeatToClient(seat_index=int(data["seat_index"]), target_client_id=str(data["target_client_id"]))
    if message_type == "create_local_bot_on_seat":
        return CreateLocalBotOnSeat(seat_index=int(data["seat_index"]), display_name=str(data["display_name"]))
    if message_type == "clear_seat":
        return ClearSeat(seat_index=int(data["seat_index"]))
    if message_type == "request_start_game":
        return RequestStartGame()
    if message_type == "leave_session":
        return LeaveSession()
    if message_type == "submit_card":
        return SubmitCard(player_id=PlayerID(str(data["player_id"])), card_value=int(data["card_value"]))
    if message_type == "submit_row_choice":
        return SubmitRowChoice(player_id=PlayerID(str(data["player_id"])), row_id=RowID(str(data["row_id"])))
    raise ValueError(f"unsupported client message type: {message_type!r}")


def server_message_to_dict(message: ServerToClientMessage) -> dict[str, object]:
    if isinstance(message, IdentityAssigned):
        return {"type": "identity_assigned", "client_id": message.client_id}
    if isinstance(message, LobbyStateUpdated):
        return {"type": "lobby_state_updated", "lobby": _lobby_view_to_dict(message.lobby)}
    if isinstance(message, LobbyActionRejected):
        return {"type": "lobby_action_rejected", "message": message.message}
    if isinstance(message, GameStarting):
        return {"type": "game_starting", "lobby": _lobby_view_to_dict(message.lobby)}
    if isinstance(message, StateUpdated):
        return {"type": "state_updated", "state": public_state_to_dict(message.state)}
    if isinstance(message, TrickRevealed):
        return {
            "type": "trick_revealed",
            "state": public_state_to_dict(message.state),
            "played_cards": [_played_card_to_dict(card) for card in message.played_cards],
            "active_player_id": None if message.active_player_id is None else str(message.active_player_id),
            "pending_card_value": message.pending_card_value,
        }
    if isinstance(message, ChooseCardRequested):
        return {"type": "choose_card_requested", "player_id": str(message.player_id), "state": player_state_to_dict(message.state)}
    if isinstance(message, ChooseRowRequested):
        return {"type": "choose_row_requested", "player_id": str(message.player_id), "state": player_state_to_dict(message.state)}
    if isinstance(message, TrickResolved):
        return {
            "type": "trick_resolved",
            "deltas": [delta_public_state_to_dict(delta) for delta in message.deltas],
            "new_round_started": message.new_round_started,
            "game_finished": message.game_finished,
        }
    if isinstance(message, SessionEnded):
        return {
            "type": "session_ended",
            "message": message.message,
            "reason": message.reason.value,
            "client_id": message.client_id,
            "display_name": message.display_name,
        }
    if isinstance(message, ServerError):
        return {"type": "server_error", "message": message.message}
    raise TypeError(f"unsupported server message type: {type(message)!r}")


def server_message_from_dict(data: dict[str, object]) -> ServerToClientMessage:
    message_type = str(data["type"])
    if message_type == "identity_assigned":
        return IdentityAssigned(client_id=str(data["client_id"]))
    if message_type == "lobby_state_updated":
        return LobbyStateUpdated(lobby=_lobby_view_from_dict(data["lobby"]))
    if message_type == "lobby_action_rejected":
        return LobbyActionRejected(message=str(data["message"]))
    if message_type == "game_starting":
        return GameStarting(lobby=_lobby_view_from_dict(data["lobby"]))
    if message_type == "state_updated":
        return StateUpdated(state=public_state_from_dict(data["state"]))
    if message_type == "trick_revealed":
        active_player_id = data.get("active_player_id")
        return TrickRevealed(
            state=public_state_from_dict(data["state"]),
            played_cards=tuple(_played_card_from_dict(card) for card in data["played_cards"]),
            active_player_id=None if active_player_id is None else PlayerID(str(active_player_id)),
            pending_card_value=None if data.get("pending_card_value") is None else int(data["pending_card_value"]),
        )
    if message_type == "choose_card_requested":
        return ChooseCardRequested(player_id=PlayerID(str(data["player_id"])), state=player_state_from_dict(data["state"]))
    if message_type == "choose_row_requested":
        return ChooseRowRequested(player_id=PlayerID(str(data["player_id"])), state=player_state_from_dict(data["state"]))
    if message_type == "trick_resolved":
        return TrickResolved(
            deltas=tuple(delta_public_state_from_dict(delta) for delta in data["deltas"]),
            new_round_started=bool(data["new_round_started"]),
            game_finished=bool(data["game_finished"]),
        )
    if message_type == "session_ended":
        client_id = data.get("client_id")
        display_name = data.get("display_name")
        return SessionEnded(
            message=str(data["message"]),
            reason=SessionEndReason(str(data["reason"])),
            client_id=None if client_id is None else str(client_id),
            display_name=None if display_name is None else str(display_name),
        )
    if message_type == "server_error":
        return ServerError(message=str(data["message"]))
    raise ValueError(f"unsupported server message type: {message_type!r}")
