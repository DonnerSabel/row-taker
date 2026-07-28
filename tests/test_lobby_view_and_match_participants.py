from row_taker.engine.game.models import PlayerID
from row_taker.engine.lobby.state import LobbySeat, LobbyState
from row_taker.server.client_registry import ClientRegistry
from row_taker.server.lobby_view import build_lobby_view
from row_taker.server.match_participants import build_match_participants
from row_taker.server.participants import Participant, ParticipantKind, ParticipantLocation


def test_lobby_view_uses_registry_metadata_without_mutating_lobby_state() -> None:
    registry = ClientRegistry()
    registry.register_participant(
        Participant("client-0", "Alice", ParticipantKind.HUMAN, ParticipantLocation.REMOTE)
    )
    lobby_state = LobbyState(
        seat_count=2, seats=(LobbySeat(0, "client-0"), LobbySeat(1, None)), game_started=False
    )

    lobby = build_lobby_view(lobby_state, registry, server_endpoint="127.0.0.1:8765")
    assert lobby.seats[0].occupant_display_name == "Alice"
    assert lobby.server_endpoint == "127.0.0.1:8765"
    registry.set_display_name("client-0", "Alicia")
    updated_lobby = build_lobby_view(lobby_state, registry)
    assert updated_lobby.seats[0].occupant_display_name == "Alicia"
    assert lobby_state.seats[0].occupant_client_id == "client-0"


def test_lobby_view_can_overlay_pending_bot_metadata() -> None:
    registry = ClientRegistry()
    lobby_state = LobbyState(
        seat_count=2, seats=(LobbySeat(0, None), LobbySeat(1, None)), game_started=False
    )
    lobby = build_lobby_view(lobby_state, registry, {1: "Bot_Bob"})
    assert lobby.seats[1].occupant_display_name == "Bot_Bob"
    assert lobby.seats[1].occupant_kind is ParticipantKind.BOT


def test_build_match_participants_from_sparse_seated_clients() -> None:
    lobby_state = LobbyState(
        seat_count=4,
        seats=(
            LobbySeat(0, "client-0"),
            LobbySeat(1, None),
            LobbySeat(2, "client-2"),
            LobbySeat(3, "client-3"),
        ),
        game_started=False,
    )
    match_participants = build_match_participants(lobby_state)
    assert match_participants.ordered_client_ids == ("client-0", "client-2", "client-3")
    assert match_participants.client_to_player_id["client-0"] == PlayerID("player-0")
    assert match_participants.client_to_player_id["client-2"] == PlayerID("player-1")
    assert match_participants.client_to_player_id["client-3"] == PlayerID("player-2")


def test_lobby_view_uses_participant_kind_enums_in_participants_and_seats() -> None:
    registry = ClientRegistry()
    registry.register_participant(
        Participant("client-0", "Alice", ParticipantKind.HUMAN, ParticipantLocation.REMOTE)
    )
    lobby_state = LobbyState(
        seat_count=2,
        seats=(LobbySeat(0, "client-0"), LobbySeat(1, None)),
        game_started=False,
    )

    lobby = build_lobby_view(lobby_state, registry)

    assert lobby.participants[0].participant_kind is ParticipantKind.HUMAN
    assert lobby.seats[0].occupant_kind is ParticipantKind.HUMAN
    assert lobby.seats[1].occupant_kind is None
