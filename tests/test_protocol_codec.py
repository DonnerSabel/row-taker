from row_taker.engine.game import setup_game
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.views import build_public_state
from row_taker.engine.lobby.state import LobbySeat, LobbyState
from row_taker.protocol.codec import (
    client_message_from_dict,
    client_message_to_dict,
    server_message_from_dict,
    server_message_to_dict,
)
from row_taker.protocol.messages import (
    AssignSeatToClient,
    CardsRevealed,
    ClearSeat,
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
    DebugStateSnapshot,
    PlayedCardView,
    RequestStartGame,
    RowChoiceCommitted,
    ServerError,
    SessionEnded,
    SessionEndReason,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
)


def _lobby_view() -> LobbyView:
    return LobbyView(
        seat_count=3,
        participants=(
            LobbyParticipantView(
                client_id="client-0", display_name="Alice", participant_kind="human", seat_index=0
            ),
            LobbyParticipantView(
                client_id="pending-bot-seat-2",
                display_name="Bot_1",
                participant_kind="bot",
                seat_index=2,
            ),
        ),
        seats=(
            LobbySeatView(
                seat_index=0,
                occupant_client_id="client-0",
                occupant_display_name="Alice",
                occupant_kind="human",
            ),
            LobbySeatView(
                seat_index=1,
                occupant_client_id=None,
                occupant_display_name=None,
                occupant_kind=None,
            ),
            LobbySeatView(
                seat_index=2,
                occupant_client_id="pending-bot-seat-2",
                occupant_display_name="Bot_1",
                occupant_kind="bot",
            ),
        ),
        game_started=False,
    )


def test_client_messages_roundtrip() -> None:
    for message in [
        JoinLobby(display_name="Alice"),
        JoinLobby(display_name="Bot_1", requested_client_id="bot-1"),
        SetDisplayName(display_name="Bob"),
        AssignSeatToClient(seat_index=1, target_client_id="client-0"),
        CreateLocalBotOnSeat(seat_index=2, display_name="Bot_X"),
        ClearSeat(seat_index=2),
        RequestStartGame(),
        LeaveSession(),
        SubmitCard(card_value=42),
        SubmitRowChoice(row_id=RowID("row-2")),
    ]:
        assert client_message_from_dict(client_message_to_dict(message)) == message


def test_server_messages_roundtrip() -> None:
    lobby = _lobby_view()
    game = setup_game(["Alice", "Bob"])
    public_state = build_public_state(game)
    messages = [
        IdentityAssigned(client_id="client-0"),
        LobbyStateUpdated(lobby=lobby),
        LobbyActionRejected(message="nope"),
        GameStarting(
            lobby=LobbyView(
                seat_count=lobby.seat_count,
                participants=lobby.participants,
                seats=lobby.seats,
                game_started=True,
            )
        ),
        StateUpdated(state=public_state, revision=1),
        CardsRevealed(
            plays=(
                PlayedCardView(
                    player_id=PlayerID("player-0"),
                    player_name="Alice",
                    card_value=17,
                ),
            ),
            revision=2,
        ),
        RowChoiceCommitted(row_id=RowID("row-0"), revision=3),
        DebugStateSnapshot(revision=4, game_state=game),
        SessionEnded(message="left", reason=SessionEndReason.QUIT, client_id="client-0", display_name="Alice"),
        ServerError(message="boom"),
    ]
    for message in messages:
        assert server_message_from_dict(server_message_to_dict(message)) == message


def test_lobby_state_is_metadata_free() -> None:
    lobby_state = LobbyState(
        seat_count=2,
        seats=(
            LobbySeat(seat_index=0, occupant_client_id="client-0"),
            LobbySeat(seat_index=1),
        ),
        game_started=False,
    )
    assert not hasattr(lobby_state, "clients")
