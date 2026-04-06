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
from row_taker.engine.lobby.config import ClientKind, MatchConfig, SeatConfig
from row_taker.engine.lobby.state import LobbyState
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ClientToServerMessage,
    ConfigureLobby,
    GameStarting,
    LobbyStateUpdated,
    ServerError,
    ServerToClientMessage,
    StartGame,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


def _seat_config_to_dict(seat: SeatConfig) -> dict[str, object]:
    return {
        "seat_index": seat.seat_index,
        "kind": seat.kind.value,
        "name": seat.name,
    }


def _seat_config_from_dict(data: object) -> SeatConfig:
    if not isinstance(data, dict):
        raise TypeError(f"seat config data must be a dict, got {type(data)!r}")
    return SeatConfig(
        seat_index=int(data["seat_index"]),
        kind=ClientKind(str(data["kind"])),
        name=str(data["name"]),
    )


def _match_config_to_dict(config: MatchConfig) -> dict[str, object]:
    return {
        "seats": [_seat_config_to_dict(seat) for seat in config.seats],
    }


def _match_config_from_dict(data: object) -> MatchConfig:
    if not isinstance(data, dict):
        raise TypeError(f"match config data must be a dict, got {type(data)!r}")
    raw_seats = data.get("seats")
    if not isinstance(raw_seats, list):
        raise TypeError(f"match config seats must be a list, got {type(raw_seats)!r}")
    return MatchConfig.from_seats([_seat_config_from_dict(seat) for seat in raw_seats])


def _lobby_state_to_dict(state: LobbyState) -> dict[str, object]:
    return {
        "match_config": None if state.match_config is None else _match_config_to_dict(state.match_config),
        "game_started": state.game_started,
    }


def _lobby_state_from_dict(data: object) -> LobbyState:
    if not isinstance(data, dict):
        raise TypeError(f"lobby state data must be a dict, got {type(data)!r}")

    raw_match_config = data.get("match_config")
    match_config = None if raw_match_config is None else _match_config_from_dict(raw_match_config)
    return LobbyState(
        match_config=match_config,
        game_started=bool(data["game_started"]),
    )


def client_message_to_dict(message: ClientToServerMessage) -> dict[str, object]:
    if isinstance(message, ConfigureLobby):
        return {
            "type": "configure_lobby",
            "match_config": _match_config_to_dict(message.match_config),
        }
    if isinstance(message, StartGame):
        return {"type": "start_game"}
    if isinstance(message, SubmitCard):
        return {
            "type": "submit_card",
            "player_id": str(message.player_id),
            "card_value": message.card_value,
        }
    if isinstance(message, SubmitRowChoice):
        return {
            "type": "submit_row_choice",
            "player_id": str(message.player_id),
            "row_id": str(message.row_id),
        }
    raise TypeError(f"unsupported client message type: {type(message)!r}")


def client_message_from_dict(data: dict[str, object]) -> ClientToServerMessage:
    message_type = str(data["type"])
    if message_type == "configure_lobby":
        return ConfigureLobby(match_config=_match_config_from_dict(data["match_config"]))
    if message_type == "start_game":
        return StartGame()
    if message_type == "submit_card":
        return SubmitCard(
            player_id=PlayerID(str(data["player_id"])),
            card_value=int(data["card_value"]),
        )
    if message_type == "submit_row_choice":
        return SubmitRowChoice(
            player_id=PlayerID(str(data["player_id"])),
            row_id=RowID(str(data["row_id"])),
        )
    raise ValueError(f"unsupported client message type: {message_type!r}")


def server_message_to_dict(message: ServerToClientMessage) -> dict[str, object]:
    if isinstance(message, LobbyStateUpdated):
        return {
            "type": "lobby_state_updated",
            "lobby_state": _lobby_state_to_dict(message.lobby_state),
        }
    if isinstance(message, GameStarting):
        return {
            "type": "game_starting",
            "lobby_state": _lobby_state_to_dict(message.lobby_state),
        }
    if isinstance(message, StateUpdated):
        return {
            "type": "state_updated",
            "state": public_state_to_dict(message.state),
        }
    if isinstance(message, ChooseCardRequested):
        return {
            "type": "choose_card_requested",
            "player_id": str(message.player_id),
            "state": player_state_to_dict(message.state),
        }
    if isinstance(message, ChooseRowRequested):
        return {
            "type": "choose_row_requested",
            "player_id": str(message.player_id),
            "state": player_state_to_dict(message.state),
        }
    if isinstance(message, TrickResolved):
        return {
            "type": "trick_resolved",
            "deltas": [delta_public_state_to_dict(delta) for delta in message.deltas],
            "new_round_started": message.new_round_started,
            "game_finished": message.game_finished,
        }
    if isinstance(message, ServerError):
        return {"type": "server_error", "message": message.message}
    raise TypeError(f"unsupported server message type: {type(message)!r}")


def server_message_from_dict(data: dict[str, object]) -> ServerToClientMessage:
    message_type = str(data["type"])
    if message_type == "lobby_state_updated":
        return LobbyStateUpdated(lobby_state=_lobby_state_from_dict(data["lobby_state"]))
    if message_type == "game_starting":
        return GameStarting(lobby_state=_lobby_state_from_dict(data["lobby_state"]))
    if message_type == "state_updated":
        return StateUpdated(state=public_state_from_dict(data["state"]))
    if message_type == "choose_card_requested":
        return ChooseCardRequested(
            player_id=PlayerID(str(data["player_id"])),
            state=player_state_from_dict(data["state"]),
        )
    if message_type == "choose_row_requested":
        return ChooseRowRequested(
            player_id=PlayerID(str(data["player_id"])),
            state=player_state_from_dict(data["state"]),
        )
    if message_type == "trick_resolved":
        return TrickResolved(
            deltas=tuple(delta_public_state_from_dict(delta) for delta in data["deltas"]),
            new_round_started=bool(data["new_round_started"]),
            game_finished=bool(data["game_finished"]),
        )
    if message_type == "server_error":
        return ServerError(message=str(data["message"]))
    raise ValueError(f"unsupported server message type: {message_type!r}")
