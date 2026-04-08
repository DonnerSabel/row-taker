import random
from dataclasses import dataclass, field

from row_taker.protocol.messages import (
    AssignSeatToClient,
    ChooseCardRequested,
    CreateLocalBotOnSeat,
    GameStarting,
    JoinLobby,
    RequestStartGame,
    SetDisplayName,
    StateUpdated,
)
from row_taker.server.local_server import LocalServer


@dataclass
class _DummyHandle:
    closed: bool = False

    def close(self) -> None:
        self.closed = True


@dataclass
class _FakeServerHandle:
    spawned: list[tuple[str, str, int, _DummyHandle]] = field(default_factory=list)

    def spawn_local_bot(self, *, display_name: str, client_id: str, seed: int) -> _DummyHandle:
        handle = _DummyHandle()
        self.spawned.append((display_name, client_id, seed, handle))
        return handle


def test_local_server_starts_match_from_multiclient_lobby_messages() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)

    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-1", JoinLobby(display_name="Bob"))
    server.handle_client_message("client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0"))
    server.handle_client_message("client-1", AssignSeatToClient(seat_index=1, target_client_id="client-1"))
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame())
    messages = [envelope.message for envelope in server.drain_outbox()]

    assert isinstance(messages[0], GameStarting)
    assert any(isinstance(message, StateUpdated) for message in messages)


def test_local_server_can_plan_bot_on_selected_seat_without_registering_it() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0"))
    server.handle_client_message("client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob"))
    lobby = server.drain_outbox()[-1].message.lobby
    seat = next(seat for seat in lobby.seats if seat.seat_index == 1)
    assert seat.occupant_client_id is not None
    assert seat.occupant_display_name == "Bot_Bob"
    assert len(server.registry.records) == 1


def test_local_server_spawns_pending_bot_only_when_game_starts() -> None:
    fake_server_handle = _FakeServerHandle()
    server = LocalServer(rng=random.Random(1234), seat_count=2, server_handle=fake_server_handle)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0"))
    server.handle_client_message("client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob"))
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame())

    assert len(fake_server_handle.spawned) == 1
    assert server.active_match is None


def test_local_server_finishes_start_when_bot_joins_with_requested_client_id() -> None:
    fake_server_handle = _FakeServerHandle()
    server = LocalServer(rng=random.Random(1234), seat_count=2, server_handle=fake_server_handle)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0"))
    server.handle_client_message("client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob"))
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame())
    _display_name, reserved_client_id, _seed, _handle = fake_server_handle.spawned[0]
    server.drain_outbox()

    adopted = server.handle_client_message(
        "conn-temp-1",
        JoinLobby(display_name="Bot_Bob", requested_client_id=reserved_client_id),
        reply_target_client_id="conn-temp-1",
    )
    envelopes = server.drain_outbox()

    assert adopted == reserved_client_id
    assert any(isinstance(envelope.message, GameStarting) for envelope in envelopes)
    assert any(isinstance(envelope.message, StateUpdated) for envelope in envelopes)
    assert any(
        isinstance(envelope.message, ChooseCardRequested) and envelope.target_client_id == "client-0"
        for envelope in envelopes
    )


def test_unknown_requested_client_id_is_rejected() -> None:
    fake_server_handle = _FakeServerHandle()
    server = LocalServer(rng=random.Random(1234), seat_count=2, server_handle=fake_server_handle)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0"))
    server.handle_client_message("client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob"))
    server.drain_outbox()

    server.handle_client_message(
        "conn-temp-1",
        JoinLobby(display_name="Bot_Bob", requested_client_id="bot-does-not-exist"),
        reply_target_client_id="conn-temp-1",
    )
    envelopes = server.drain_outbox()
    assert envelopes[0].target_client_id == "conn-temp-1"


def test_registry_is_only_source_of_participant_metadata() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-0", SetDisplayName(display_name="Alicia"))
    participant = server.registry.get_participant("client-0")
    assert participant.display_name == "Alicia"
    assert not hasattr(server.lobby_state, "clients")
