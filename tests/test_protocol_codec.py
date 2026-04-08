from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.lobby.config import ClientKind
from row_taker.engine.lobby.state import ConnectedClient, LobbySeat, LobbyState
from row_taker.protocol.codec import (
    client_message_from_dict,
    client_message_to_dict,
    server_message_from_dict,
    server_message_to_dict,
)
from row_taker.protocol.messages import (
    AssignSeatToClient,
    CreateLocalBotOnSeat,
    GameStarting,
    JoinLobby,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    ServerError,
    SetDisplayName,
    SubmitCard,
    SubmitRowChoice,
    ClearSeat,
)


def _lobby_state() -> LobbyState:
    return LobbyState(
        seat_count=3,
        clients=(
            ConnectedClient(client_id='client-0', display_name='Alice', kind=ClientKind.HUMAN),
            ConnectedClient(client_id='bot-1', display_name='Bot_1', kind=ClientKind.RANDOM_BOT),
        ),
        seats=(
            LobbySeat(seat_index=0, occupant_client_id='client-0'),
            LobbySeat(seat_index=1),
            LobbySeat(seat_index=2, occupant_client_id='bot-1'),
        ),
        game_started=False,
    )


def test_client_messages_roundtrip() -> None:
    for message in [
        JoinLobby(display_name='Alice'),
        SetDisplayName(display_name='Bob'),
        AssignSeatToClient(seat_index=1, target_client_id='client-0'),
        CreateLocalBotOnSeat(seat_index=2, display_name='Bot_X'),
        ClearSeat(seat_index=2),
        RequestStartGame(),
        SubmitCard(player_id=PlayerID('player-0'), card_value=42),
        SubmitRowChoice(player_id=PlayerID('player-1'), row_id=RowID('row-2')),
    ]:
        assert client_message_from_dict(client_message_to_dict(message)) == message


def test_server_messages_roundtrip() -> None:
    lobby_state = _lobby_state()
    messages = [
        LobbyStateUpdated(lobby_state=lobby_state),
        LobbyActionRejected(message='nope'),
        GameStarting(lobby_state=LobbyState(seat_count=3, clients=lobby_state.clients, seats=lobby_state.seats, game_started=True)),
        ServerError(message='boom'),
    ]
    for message in messages:
        assert server_message_from_dict(server_message_to_dict(message)) == message
