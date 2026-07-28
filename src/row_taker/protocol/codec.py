from __future__ import annotations

from collections.abc import Mapping

from row_taker.engine.game import PlayerID, RowID
from row_taker.engine.game.state_mappers import (
    game_state_from_dict,
    game_state_to_dict,
    player_state_from_dict,
    player_state_to_dict,
    public_state_from_dict,
    public_state_to_dict,
)
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import (
    AssignSeatToClient,
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    DebugStateSnapshot,
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
    RowChoiceCommitted,
    ServerError,
    ServerToClientMessage,
    SessionEnded,
    SessionEndReason,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
)
from row_taker.serialization.json_values import (
    optional_int,
    optional_str,
    require_bool,
    require_field,
    require_int,
    require_object,
    require_sequence,
    require_str,
)


def _lobby_participant_to_dict(participant: LobbyParticipantView) -> dict[str, object]:
    return {
        "client_id": participant.client_id,
        "display_name": participant.display_name,
        "participant_kind": str(participant.participant_kind),
        "seat_index": participant.seat_index,
        "endpoint": participant.endpoint,
    }


def _lobby_participant_from_dict(data: object, *, context: str) -> LobbyParticipantView:
    value = require_object(data, context=context)
    return LobbyParticipantView(
        client_id=require_str(
            require_field(value, "client_id", context=context), context=f"{context}.client_id"
        ),
        display_name=require_str(
            require_field(value, "display_name", context=context),
            context=f"{context}.display_name",
        ),
        participant_kind=ParticipantKind(
            require_str(
                require_field(value, "participant_kind", context=context),
                context=f"{context}.participant_kind",
            )
        ),
        seat_index=optional_int(value.get("seat_index"), context=f"{context}.seat_index"),
        endpoint=optional_str(value.get("endpoint"), context=f"{context}.endpoint"),
    )


def _lobby_seat_to_dict(seat: LobbySeatView) -> dict[str, object]:
    return {
        "seat_index": seat.seat_index,
        "occupant_client_id": seat.occupant_client_id,
        "occupant_display_name": seat.occupant_display_name,
        "occupant_kind": None if seat.occupant_kind is None else str(seat.occupant_kind),
        "occupant_endpoint": seat.occupant_endpoint,
    }


def _lobby_seat_from_dict(data: object, *, context: str) -> LobbySeatView:
    value = require_object(data, context=context)
    occupant_kind_value = value.get("occupant_kind")
    return LobbySeatView(
        seat_index=require_int(
            require_field(value, "seat_index", context=context), context=f"{context}.seat_index"
        ),
        occupant_client_id=optional_str(
            value.get("occupant_client_id"), context=f"{context}.occupant_client_id"
        ),
        occupant_display_name=optional_str(
            value.get("occupant_display_name"), context=f"{context}.occupant_display_name"
        ),
        occupant_kind=None
        if occupant_kind_value is None
        else ParticipantKind(require_str(occupant_kind_value, context=f"{context}.occupant_kind")),
        occupant_endpoint=optional_str(
            value.get("occupant_endpoint"), context=f"{context}.occupant_endpoint"
        ),
    )


def _lobby_view_to_dict(lobby: LobbyView) -> dict[str, object]:
    return {
        "seat_count": lobby.seat_count,
        "participants": [
            _lobby_participant_to_dict(participant) for participant in lobby.participants
        ],
        "seats": [_lobby_seat_to_dict(seat) for seat in lobby.seats],
        "game_started": lobby.game_started,
        "server_endpoint": lobby.server_endpoint,
    }


def _lobby_view_from_dict(data: object, *, context: str = "lobby") -> LobbyView:
    value = require_object(data, context=context)
    participants = require_sequence(
        require_field(value, "participants", context=context), context=f"{context}.participants"
    )
    seats = require_sequence(
        require_field(value, "seats", context=context), context=f"{context}.seats"
    )
    return LobbyView(
        seat_count=require_int(
            require_field(value, "seat_count", context=context), context=f"{context}.seat_count"
        ),
        participants=tuple(
            _lobby_participant_from_dict(participant, context=f"{context}.participants[{index}]")
            for index, participant in enumerate(participants)
        ),
        seats=tuple(
            _lobby_seat_from_dict(seat, context=f"{context}.seats[{index}]")
            for index, seat in enumerate(seats)
        ),
        game_started=require_bool(
            require_field(value, "game_started", context=context),
            context=f"{context}.game_started",
        ),
        server_endpoint=optional_str(
            value.get("server_endpoint"), context=f"{context}.server_endpoint"
        ),
    )


def _played_card_to_dict(card: PlayedCardView) -> dict[str, object]:
    return {
        "player_id": str(card.player_id),
        "player_name": card.player_name,
        "card_value": card.card_value,
    }


def _played_card_from_dict(data: object, *, context: str) -> PlayedCardView:
    value = require_object(data, context=context)
    return PlayedCardView(
        player_id=PlayerID(
            require_str(
                require_field(value, "player_id", context=context),
                context=f"{context}.player_id",
            )
        ),
        player_name=require_str(
            require_field(value, "player_name", context=context),
            context=f"{context}.player_name",
        ),
        card_value=require_int(
            require_field(value, "card_value", context=context),
            context=f"{context}.card_value",
        ),
    )


def client_message_to_dict(message: ClientToServerMessage) -> dict[str, object]:
    if isinstance(message, JoinLobby):
        return {
            "type": "join_lobby",
            "display_name": message.display_name,
            "requested_client_id": message.requested_client_id,
        }
    if isinstance(message, SetDisplayName):
        return {"type": "set_display_name", "display_name": message.display_name}
    if isinstance(message, AssignSeatToClient):
        return {
            "type": "assign_seat_to_client",
            "seat_index": message.seat_index,
            "target_client_id": message.target_client_id,
        }
    if isinstance(message, CreateLocalBotOnSeat):
        return {
            "type": "create_local_bot_on_seat",
            "seat_index": message.seat_index,
            "display_name": message.display_name,
        }
    if isinstance(message, ClearSeat):
        return {"type": "clear_seat", "seat_index": message.seat_index}
    if isinstance(message, RequestStartGame):
        return {"type": "request_start_game"}
    if isinstance(message, LeaveSession):
        return {"type": "leave_session"}
    if isinstance(message, SubmitCard):
        return {"type": "submit_card", "card_value": message.card_value}
    if isinstance(message, SubmitRowChoice):
        return {"type": "submit_row_choice", "row_id": str(message.row_id)}
    raise TypeError(f"unsupported client message type: {type(message)!r}")


def client_message_from_dict(data: Mapping[str, object]) -> ClientToServerMessage:
    context = "client_message"
    message_type = require_str(
        require_field(data, "type", context=context), context="client_message.type"
    )
    if message_type == "join_lobby":
        return JoinLobby(
            display_name=require_str(
                require_field(data, "display_name", context=context),
                context="join_lobby.display_name",
            ),
            requested_client_id=optional_str(
                data.get("requested_client_id"), context="join_lobby.requested_client_id"
            ),
        )
    if message_type == "set_display_name":
        return SetDisplayName(
            display_name=require_str(
                require_field(data, "display_name", context=context),
                context="set_display_name.display_name",
            )
        )
    if message_type == "assign_seat_to_client":
        return AssignSeatToClient(
            seat_index=require_int(
                require_field(data, "seat_index", context=context),
                context="assign_seat_to_client.seat_index",
            ),
            target_client_id=require_str(
                require_field(data, "target_client_id", context=context),
                context="assign_seat_to_client.target_client_id",
            ),
        )
    if message_type == "create_local_bot_on_seat":
        return CreateLocalBotOnSeat(
            seat_index=require_int(
                require_field(data, "seat_index", context=context),
                context="create_local_bot_on_seat.seat_index",
            ),
            display_name=require_str(
                require_field(data, "display_name", context=context),
                context="create_local_bot_on_seat.display_name",
            ),
        )
    if message_type == "clear_seat":
        return ClearSeat(
            seat_index=require_int(
                require_field(data, "seat_index", context=context), context="clear_seat.seat_index"
            )
        )
    if message_type == "request_start_game":
        return RequestStartGame()
    if message_type == "leave_session":
        return LeaveSession()
    if message_type == "submit_card":
        return SubmitCard(
            card_value=require_int(
                require_field(data, "card_value", context=context),
                context="submit_card.card_value",
            )
        )
    if message_type == "submit_row_choice":
        return SubmitRowChoice(
            row_id=RowID(
                require_str(
                    require_field(data, "row_id", context=context),
                    context="submit_row_choice.row_id",
                )
            )
        )
    raise TypeError(f"unsupported client message type: {message_type!r}")


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
        return {
            "type": "state_updated",
            "state": public_state_to_dict(message.state),
            "revision": message.revision,
        }
    if isinstance(message, CardsRevealed):
        return {
            "type": "cards_revealed",
            "plays": [_played_card_to_dict(card) for card in message.plays],
            "revision": message.revision,
        }
    if isinstance(message, RowChoiceCommitted):
        return {
            "type": "row_choice_committed",
            "row_id": str(message.row_id),
            "revision": message.revision,
        }
    if isinstance(message, ChooseCardRequested):
        return {
            "type": "choose_card_requested",
            "player_id": str(message.player_id),
            "state": player_state_to_dict(message.state),
            "revision": message.revision,
        }
    if isinstance(message, ChooseRowRequested):
        return {
            "type": "choose_row_requested",
            "player_id": str(message.player_id),
            "state": player_state_to_dict(message.state),
            "revision": message.revision,
        }
    if isinstance(message, DebugStateSnapshot):
        return {
            "type": "debug_state_snapshot",
            "revision": message.revision,
            "game_state": game_state_to_dict(message.game_state),
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


def server_message_from_dict(data: Mapping[str, object]) -> ServerToClientMessage:
    context = "server_message"
    message_type = require_str(
        require_field(data, "type", context=context), context="server_message.type"
    )
    if message_type == "identity_assigned":
        return IdentityAssigned(
            client_id=require_str(
                require_field(data, "client_id", context=context),
                context="identity_assigned.client_id",
            )
        )
    if message_type == "lobby_state_updated":
        return LobbyStateUpdated(
            lobby=_lobby_view_from_dict(
                require_field(data, "lobby", context=context), context="lobby_state_updated.lobby"
            )
        )
    if message_type == "lobby_action_rejected":
        return LobbyActionRejected(
            message=require_str(
                require_field(data, "message", context=context),
                context="lobby_action_rejected.message",
            )
        )
    if message_type == "game_starting":
        return GameStarting(
            lobby=_lobby_view_from_dict(
                require_field(data, "lobby", context=context), context="game_starting.lobby"
            )
        )
    if message_type == "state_updated":
        return StateUpdated(
            state=public_state_from_dict(
                require_object(
                    require_field(data, "state", context=context), context="state_updated.state"
                )
            ),
            revision=optional_int(data.get("revision"), context="state_updated.revision"),
        )
    if message_type == "cards_revealed":
        values = require_sequence(
            require_field(data, "plays", context=context), context="cards_revealed.plays"
        )
        return CardsRevealed(
            plays=tuple(
                _played_card_from_dict(value, context=f"cards_revealed.plays[{index}]")
                for index, value in enumerate(values)
            ),
            revision=optional_int(data.get("revision"), context="cards_revealed.revision"),
        )
    if message_type == "row_choice_committed":
        return RowChoiceCommitted(
            row_id=RowID(
                require_str(
                    require_field(data, "row_id", context=context),
                    context="row_choice_committed.row_id",
                )
            ),
            revision=optional_int(data.get("revision"), context="row_choice_committed.revision"),
        )
    if message_type == "choose_card_requested":
        return ChooseCardRequested(
            player_id=PlayerID(
                require_str(
                    require_field(data, "player_id", context=context),
                    context="choose_card_requested.player_id",
                )
            ),
            state=player_state_from_dict(
                require_object(
                    require_field(data, "state", context=context),
                    context="choose_card_requested.state",
                )
            ),
            revision=optional_int(data.get("revision"), context="choose_card_requested.revision"),
        )
    if message_type == "choose_row_requested":
        return ChooseRowRequested(
            player_id=PlayerID(
                require_str(
                    require_field(data, "player_id", context=context),
                    context="choose_row_requested.player_id",
                )
            ),
            state=player_state_from_dict(
                require_object(
                    require_field(data, "state", context=context),
                    context="choose_row_requested.state",
                )
            ),
            revision=optional_int(data.get("revision"), context="choose_row_requested.revision"),
        )
    if message_type == "debug_state_snapshot":
        return DebugStateSnapshot(
            revision=require_int(
                require_field(data, "revision", context=context),
                context="debug_state_snapshot.revision",
            ),
            game_state=game_state_from_dict(
                require_object(
                    require_field(data, "game_state", context=context),
                    context="debug_state_snapshot.game_state",
                )
            ),
        )
    if message_type == "session_ended":
        return SessionEnded(
            message=require_str(
                require_field(data, "message", context=context), context="session_ended.message"
            ),
            reason=SessionEndReason(
                require_str(
                    require_field(data, "reason", context=context),
                    context="session_ended.reason",
                )
            ),
            client_id=optional_str(data.get("client_id"), context="session_ended.client_id"),
            display_name=optional_str(
                data.get("display_name"), context="session_ended.display_name"
            ),
        )
    if message_type == "server_error":
        return ServerError(
            message=require_str(
                require_field(data, "message", context=context), context="server_error.message"
            )
        )
    raise TypeError(f"unsupported server message type: {message_type!r}")
