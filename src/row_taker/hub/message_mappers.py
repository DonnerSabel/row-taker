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
from row_taker.hub.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ClientToHubMessage,
    HubToClientMessage,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


def client_message_to_dict(message: ClientToHubMessage) -> dict[str, object]:
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


def client_message_from_dict(data: dict[str, object]) -> ClientToHubMessage:
    message_type = str(data['type'])
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


def hub_message_to_dict(message: HubToClientMessage) -> dict[str, object]:
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
    raise TypeError(f'unsupported hub message type: {type(message)!r}')


def hub_message_from_dict(data: dict[str, object]) -> HubToClientMessage:
    message_type = str(data['type'])
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
    raise ValueError(f'unsupported hub message type: {message_type!r}')
