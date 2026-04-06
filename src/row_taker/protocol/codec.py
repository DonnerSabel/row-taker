from __future__ import annotations

from row_taker.engine.models import PlayerID, RowID
from row_taker.engine.state_mappers import (
    delta_public_state_from_dict,
    delta_public_state_to_dict,
    player_state_from_dict,
    player_state_to_dict,
    public_state_from_dict,
    public_state_to_dict,
)
from row_taker.hub.match_config import ClientKind, MatchConfig, SeatConfig
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ClientToServerMessage,
    ConfigureLobby,
    GameStarting,
    LobbyStateUpdated,
    ServerToClientMessage,
    StartGame,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


def _match_config_to_dict(match_config: MatchConfig) -> dict[str, object]:
    return {
        'seats': [
            {
                'seat_index': seat.seat_index,
                'kind': seat.kind.value,
                'name': seat.name,
            }
            for seat in match_config.seats
        ]
    }



def _match_config_from_dict(data: object) -> MatchConfig:
    if not isinstance(data, dict):
        raise TypeError(f'match config data must be a dict, got {type(data)!r}')

    seats_data = data['seats']
    if not isinstance(seats_data, list):
        raise TypeError(f'match config seats must be a list, got {type(seats_data)!r}')

    seats = [
        SeatConfig(
            seat_index=int(seat_data['seat_index']),
            kind=ClientKind(str(seat_data['kind'])),
            name=str(seat_data['name']),
        )
        for seat_data in seats_data
    ]
    return MatchConfig.from_seats(seats)



def client_message_to_dict(message: ClientToServerMessage) -> dict[str, object]:
    if isinstance(message, ConfigureLobby):
        return {
            'type': 'configure_lobby',
            'match_config': _match_config_to_dict(message.match_config),
        }
    if isinstance(message, StartGame):
        return {'type': 'start_game'}
    if isinstance(message, SubmitCard):
        return {
            'type': 'submit_card',
            'player_id': str(message.player_id),
            'card_value': message.card_value,
        }
    if isinstance(message, SubmitRowChoice):
        return {
            'type': 'submit_row_choice',
            'player_id': str(message.player_id),
            'row_id': str(message.row_id),
        }
    raise TypeError(f'unsupported client message type: {type(message)!r}')



def client_message_from_dict(data: dict[str, object]) -> ClientToServerMessage:
    message_type = str(data['type'])
    if message_type == 'configure_lobby':
        return ConfigureLobby(match_config=_match_config_from_dict(data['match_config']))
    if message_type == 'start_game':
        return StartGame()
    if message_type == 'submit_card':
        return SubmitCard(
            player_id=PlayerID(str(data['player_id'])),
            card_value=int(data['card_value']),
        )
    if message_type == 'submit_row_choice':
        return SubmitRowChoice(
            player_id=PlayerID(str(data['player_id'])),
            row_id=RowID(str(data['row_id'])),
        )
    raise ValueError(f'unsupported client message type: {message_type!r}')



def server_message_to_dict(message: ServerToClientMessage) -> dict[str, object]:
    if isinstance(message, LobbyStateUpdated):
        return {
            'type': 'lobby_state_updated',
            'match_config': _match_config_to_dict(message.match_config),
        }
    if isinstance(message, GameStarting):
        return {
            'type': 'game_starting',
            'match_config': _match_config_to_dict(message.match_config),
        }
    if isinstance(message, StateUpdated):
        return {
            'type': 'state_updated',
            'state': public_state_to_dict(message.state),
        }
    if isinstance(message, ChooseCardRequested):
        return {
            'type': 'choose_card_requested',
            'player_id': str(message.player_id),
            'state': player_state_to_dict(message.state),
        }
    if isinstance(message, ChooseRowRequested):
        return {
            'type': 'choose_row_requested',
            'player_id': str(message.player_id),
            'state': player_state_to_dict(message.state),
        }
    if isinstance(message, TrickResolved):
        return {
            'type': 'trick_resolved',
            'deltas': [delta_public_state_to_dict(delta) for delta in message.deltas],
            'new_round_started': message.new_round_started,
            'game_finished': message.game_finished,
        }
    raise TypeError(f'unsupported server message type: {type(message)!r}')



def server_message_from_dict(data: dict[str, object]) -> ServerToClientMessage:
    message_type = str(data['type'])
    if message_type == 'lobby_state_updated':
        return LobbyStateUpdated(match_config=_match_config_from_dict(data['match_config']))
    if message_type == 'game_starting':
        return GameStarting(match_config=_match_config_from_dict(data['match_config']))
    if message_type == 'state_updated':
        return StateUpdated(state=public_state_from_dict(data['state']))
    if message_type == 'choose_card_requested':
        return ChooseCardRequested(
            player_id=PlayerID(str(data['player_id'])),
            state=player_state_from_dict(data['state']),
        )
    if message_type == 'choose_row_requested':
        return ChooseRowRequested(
            player_id=PlayerID(str(data['player_id'])),
            state=player_state_from_dict(data['state']),
        )
    if message_type == 'trick_resolved':
        return TrickResolved(
            deltas=tuple(delta_public_state_from_dict(delta) for delta in data['deltas']),
            new_round_started=bool(data['new_round_started']),
            game_finished=bool(data['game_finished']),
        )
    raise ValueError(f'unsupported server message type: {message_type!r}')
