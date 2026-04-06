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
from row_taker.engine.lobby.config import ClientKind
from row_taker.engine.lobby.state import ConnectedClient, LobbySeat, LobbyState
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ChooseSeat,
    ClearBotSeats,
    ClientToServerMessage,
    FillEmptySeatsWithBots,
    GameStarting,
    JoinLobby,
    LeaveSeat,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    ServerError,
    ServerToClientMessage,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


def _connected_client_to_dict(client: ConnectedClient) -> dict[str, object]:
    return {"client_id": client.client_id, "display_name": client.display_name}


def _connected_client_from_dict(data: object) -> ConnectedClient:
    if not isinstance(data, dict):
        raise TypeError(f'connected client must be a dict, got {type(data)!r}')
    return ConnectedClient(client_id=str(data['client_id']), display_name=str(data['display_name']))


def _lobby_seat_to_dict(seat: LobbySeat) -> dict[str, object]:
    return {
        'seat_index': seat.seat_index,
        'kind': None if seat.kind is None else seat.kind.value,
        'name': seat.name,
        'client_id': seat.client_id,
    }


def _lobby_seat_from_dict(data: object) -> LobbySeat:
    if not isinstance(data, dict):
        raise TypeError(f'lobby seat must be a dict, got {type(data)!r}')
    raw_kind = data.get('kind')
    kind = None if raw_kind is None else ClientKind(str(raw_kind))
    return LobbySeat(
        seat_index=int(data['seat_index']),
        kind=kind,
        name=None if data.get('name') is None else str(data['name']),
        client_id=None if data.get('client_id') is None else str(data['client_id']),
    )


def _lobby_state_to_dict(state: LobbyState) -> dict[str, object]:
    return {
        'seat_count': state.seat_count,
        'clients': [_connected_client_to_dict(client) for client in state.clients],
        'seats': [_lobby_seat_to_dict(seat) for seat in state.seats],
        'game_started': state.game_started,
    }


def _lobby_state_from_dict(data: object) -> LobbyState:
    if not isinstance(data, dict):
        raise TypeError(f'lobby state data must be a dict, got {type(data)!r}')
    return LobbyState(
        seat_count=int(data['seat_count']),
        clients=tuple(_connected_client_from_dict(client) for client in data['clients']),
        seats=tuple(_lobby_seat_from_dict(seat) for seat in data['seats']),
        game_started=bool(data['game_started']),
    )


def client_message_to_dict(message: ClientToServerMessage) -> dict[str, object]:
    if isinstance(message, JoinLobby):
        return {'type': 'join_lobby', 'display_name': message.display_name}
    if isinstance(message, SetDisplayName):
        return {'type': 'set_display_name', 'display_name': message.display_name}
    if isinstance(message, ChooseSeat):
        return {'type': 'choose_seat', 'seat_index': message.seat_index}
    if isinstance(message, LeaveSeat):
        return {'type': 'leave_seat'}
    if isinstance(message, FillEmptySeatsWithBots):
        return {'type': 'fill_empty_seats_with_bots'}
    if isinstance(message, ClearBotSeats):
        return {'type': 'clear_bot_seats'}
    if isinstance(message, RequestStartGame):
        return {'type': 'request_start_game'}
    if isinstance(message, SubmitCard):
        return {'type': 'submit_card', 'player_id': str(message.player_id), 'card_value': message.card_value}
    if isinstance(message, SubmitRowChoice):
        return {'type': 'submit_row_choice', 'player_id': str(message.player_id), 'row_id': str(message.row_id)}
    raise TypeError(f'unsupported client message type: {type(message)!r}')


def client_message_from_dict(data: dict[str, object]) -> ClientToServerMessage:
    message_type = str(data['type'])
    if message_type == 'join_lobby':
        return JoinLobby(display_name=str(data['display_name']))
    if message_type == 'set_display_name':
        return SetDisplayName(display_name=str(data['display_name']))
    if message_type == 'choose_seat':
        return ChooseSeat(seat_index=int(data['seat_index']))
    if message_type == 'leave_seat':
        return LeaveSeat()
    if message_type == 'fill_empty_seats_with_bots':
        return FillEmptySeatsWithBots()
    if message_type == 'clear_bot_seats':
        return ClearBotSeats()
    if message_type == 'request_start_game':
        return RequestStartGame()
    if message_type == 'submit_card':
        return SubmitCard(player_id=PlayerID(str(data['player_id'])), card_value=int(data['card_value']))
    if message_type == 'submit_row_choice':
        return SubmitRowChoice(player_id=PlayerID(str(data['player_id'])), row_id=RowID(str(data['row_id'])))
    raise ValueError(f'unsupported client message type: {message_type!r}')


def server_message_to_dict(message: ServerToClientMessage) -> dict[str, object]:
    if isinstance(message, LobbyStateUpdated):
        return {'type': 'lobby_state_updated', 'lobby_state': _lobby_state_to_dict(message.lobby_state)}
    if isinstance(message, LobbyActionRejected):
        return {'type': 'lobby_action_rejected', 'message': message.message}
    if isinstance(message, GameStarting):
        return {'type': 'game_starting', 'lobby_state': _lobby_state_to_dict(message.lobby_state)}
    if isinstance(message, StateUpdated):
        return {'type': 'state_updated', 'state': public_state_to_dict(message.state)}
    if isinstance(message, ChooseCardRequested):
        return {'type': 'choose_card_requested', 'player_id': str(message.player_id), 'state': player_state_to_dict(message.state)}
    if isinstance(message, ChooseRowRequested):
        return {'type': 'choose_row_requested', 'player_id': str(message.player_id), 'state': player_state_to_dict(message.state)}
    if isinstance(message, TrickResolved):
        return {
            'type': 'trick_resolved',
            'deltas': [delta_public_state_to_dict(delta) for delta in message.deltas],
            'new_round_started': message.new_round_started,
            'game_finished': message.game_finished,
        }
    if isinstance(message, ServerError):
        return {'type': 'server_error', 'message': message.message}
    raise TypeError(f'unsupported server message type: {type(message)!r}')


def server_message_from_dict(data: dict[str, object]) -> ServerToClientMessage:
    message_type = str(data['type'])
    if message_type == 'lobby_state_updated':
        return LobbyStateUpdated(lobby_state=_lobby_state_from_dict(data['lobby_state']))
    if message_type == 'lobby_action_rejected':
        return LobbyActionRejected(message=str(data['message']))
    if message_type == 'game_starting':
        return GameStarting(lobby_state=_lobby_state_from_dict(data['lobby_state']))
    if message_type == 'state_updated':
        return StateUpdated(state=public_state_from_dict(data['state']))
    if message_type == 'choose_card_requested':
        return ChooseCardRequested(player_id=PlayerID(str(data['player_id'])), state=player_state_from_dict(data['state']))
    if message_type == 'choose_row_requested':
        return ChooseRowRequested(player_id=PlayerID(str(data['player_id'])), state=player_state_from_dict(data['state']))
    if message_type == 'trick_resolved':
        return TrickResolved(
            deltas=tuple(delta_public_state_from_dict(delta) for delta in data['deltas']),
            new_round_started=bool(data['new_round_started']),
            game_finished=bool(data['game_finished']),
        )
    if message_type == 'server_error':
        return ServerError(message=str(data['message']))
    raise ValueError(f'unsupported server message type: {message_type!r}')
