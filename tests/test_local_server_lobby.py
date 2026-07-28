import random
from dataclasses import dataclass, field

from row_taker.engine.game.cards import Card
from row_taker.protocol.messages import (
    AssignSeatToClient,
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    CreateLocalBotOnSeat,
    GameStarting,
    JoinLobby,
    LeaveSession,
    LobbyActionRejected,
    RequestStartGame,
    SessionEnded,
    SessionEndReason,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
)
from row_taker.server.local_server import LocalServer


@dataclass
class _DummyHandle:
    closed: bool = False
    exit_code: int | None = None

    def poll(self) -> int | None:
        return self.exit_code

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
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-1", AssignSeatToClient(seat_index=1, target_client_id="client-1")
    )
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame())
    messages = [envelope.message for envelope in server.drain_outbox()]

    assert isinstance(messages[0], GameStarting)
    assert any(isinstance(message, StateUpdated) for message in messages)


def test_local_server_can_plan_bot_on_selected_seat_without_registering_it() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob")
    )
    lobby = server.drain_outbox()[-1].message.lobby
    seat = next(seat for seat in lobby.seats if seat.seat_index == 1)
    assert seat.occupant_client_id is not None
    assert seat.occupant_display_name == "Bot_Bob"
    assert len(server.registry.list_participants()) == 1


def test_local_server_spawns_pending_bot_only_when_game_starts() -> None:
    fake_server_handle = _FakeServerHandle()
    server = LocalServer(rng=random.Random(1234), seat_count=2, server_handle=fake_server_handle)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob")
    )
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame())

    assert len(fake_server_handle.spawned) == 1
    assert server.active_match is None


def test_local_server_finishes_start_when_bot_joins_with_requested_client_id() -> None:
    fake_server_handle = _FakeServerHandle()
    server = LocalServer(rng=random.Random(1234), seat_count=2, server_handle=fake_server_handle)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob")
    )
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
        isinstance(envelope.message, ChooseCardRequested)
        and envelope.target_client_id == "client-0"
        for envelope in envelopes
    )


def test_unknown_requested_client_id_is_rejected() -> None:
    fake_server_handle = _FakeServerHandle()
    server = LocalServer(rng=random.Random(1234), seat_count=2, server_handle=fake_server_handle)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob")
    )
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


def test_leave_session_aborts_active_match_for_remaining_clients() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.register_connection("client-0", endpoint_display="10.0.0.1:1000")
    server.register_connection("client-1", endpoint_display="10.0.0.2:1000")
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-1", JoinLobby(display_name="Bob"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-1", AssignSeatToClient(seat_index=1, target_client_id="client-1")
    )
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame())
    server.drain_outbox()

    server.handle_client_message("client-0", LeaveSession())
    envelopes = server.drain_outbox()

    session_ended = [
        envelope for envelope in envelopes if isinstance(envelope.message, SessionEnded)
    ]
    assert len(session_ended) == 1
    assert session_ended[0].target_client_id == "client-1"
    assert session_ended[0].message.reason == SessionEndReason.QUIT
    assert "Alice" in session_ended[0].message.message


def test_game_messages_are_revisioned_when_routed() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-1", JoinLobby(display_name="Bob"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-1", AssignSeatToClient(seat_index=1, target_client_id="client-1")
    )
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame(), reply_target_client_id="client-0")
    envelopes = server.drain_outbox()
    revisions = [env.message.revision for env in envelopes if isinstance(env.message, StateUpdated)]
    assert revisions == [1]

    match = server.active_match
    assert match is not None
    state = match.state
    state.players[0].hand = [Card(1)]
    state.players[1].hand = [Card(90)]
    for index, row in enumerate(state.rows):
        row.cards = [Card((index + 1) * 10)]

    server.handle_client_message(
        "client-0", SubmitCard(card_value=1), reply_target_client_id="client-0"
    )
    server.drain_outbox()
    server.handle_client_message(
        "client-1", SubmitCard(card_value=90), reply_target_client_id="client-1"
    )
    envelopes = server.drain_outbox()
    tagged = [
        env.message
        for env in envelopes
        if isinstance(env.message, CardsRevealed | ChooseRowRequested)
    ]
    assert [message.revision for message in tagged] == [4, 5]


def test_match_abort_does_not_broadcast_lobby_state_during_session_teardown() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.register_connection("client-0", endpoint_display="10.0.0.1:1000")
    server.register_connection("client-1", endpoint_display="10.0.0.2:1000")
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-1", JoinLobby(display_name="Bob"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-1", AssignSeatToClient(seat_index=1, target_client_id="client-1")
    )
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame())
    server.drain_outbox()

    server.handle_client_message("client-0", LeaveSession())
    server.drain_outbox()
    server.disconnect_client("client-1")
    envelopes = server.drain_outbox()

    assert not any(hasattr(envelope.message, "lobby") for envelope in envelopes)


def _last_rejection(server: LocalServer) -> LobbyActionRejected:
    messages = [envelope.message for envelope in server.drain_outbox()]
    rejection = next(message for message in messages if isinstance(message, LobbyActionRejected))
    return rejection


def test_duplicate_pending_bot_name_is_rejected_case_insensitively() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=3)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.drain_outbox()

    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob")
    )
    server.drain_outbox()
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=2, display_name=" bot_bob ")
    )

    rejection = _last_rejection(server)
    assert "duplicate participant display name" in rejection.message
    assert server.bot_manager.pending_display_names() == {1: "Bot_Bob"}


def test_pending_bot_name_must_not_conflict_with_connected_participant() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.drain_outbox()

    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name=" alice ")
    )

    rejection = _last_rejection(server)
    assert "duplicate participant display name" in rejection.message
    assert server.bot_manager.pending_display_names() == {}


def test_human_join_and_rename_must_not_conflict_with_pending_bot() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=3)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob")
    )
    server.drain_outbox()

    server.handle_client_message("client-1", JoinLobby(display_name="bot_bob"))
    join_rejection = _last_rejection(server)
    assert "duplicate participant display name" in join_rejection.message
    assert not server.registry.has("client-1")

    server.handle_client_message("client-1", JoinLobby(display_name="Clara"))
    server.drain_outbox()
    server.handle_client_message("client-1", SetDisplayName(display_name="BOT_BOB"))
    rename_rejection = _last_rejection(server)
    assert "duplicate participant display name" in rename_rejection.message
    assert server.registry.get_participant("client-1").display_name == "Clara"


def test_same_pending_bot_seat_may_keep_name_and_clearing_releases_it() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=3)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_Bob")
    )
    server.drain_outbox()

    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name=" bot_bob ")
    )
    messages = [envelope.message for envelope in server.drain_outbox()]
    assert not any(isinstance(message, LobbyActionRejected) for message in messages)
    assert server.bot_manager.pending_display_names() == {1: "bot_bob"}

    server.handle_client_message("client-0", ClearSeat(seat_index=1))
    server.drain_outbox()
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=2, display_name="Bot_Bob")
    )
    messages = [envelope.message for envelope in server.drain_outbox()]
    assert not any(isinstance(message, LobbyActionRejected) for message in messages)
    assert server.bot_manager.pending_display_names() == {2: "Bot_Bob"}


@dataclass
class _FailingServerHandle:
    fail_on_call: int
    spawned: list[_DummyHandle] = field(default_factory=list)
    calls: int = 0

    def spawn_local_bot(
        self,
        *,
        display_name: str,
        client_id: str,
        seed: int,
    ) -> _DummyHandle:
        del display_name, client_id, seed
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise RuntimeError("spawn failed")
        handle = _DummyHandle()
        self.spawned.append(handle)
        return handle


@dataclass
class _FakeClock:
    value: float = 0.0

    def __call__(self) -> float:
        return self.value


def _configure_human_and_two_bots(
    server: LocalServer,
    *,
    first_bot_name: str = "Bot_A",
    second_bot_name: str = "Bot_B",
) -> None:
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name=first_bot_name)
    )
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=2, display_name=second_bot_name)
    )
    server.drain_outbox()


def test_local_server_rolls_back_partial_bot_spawn_failure() -> None:
    fake_server_handle = _FailingServerHandle(fail_on_call=2)
    server = LocalServer(
        rng=random.Random(1234),
        seat_count=3,
        server_handle=fake_server_handle,
    )
    _configure_human_and_two_bots(server)

    server.handle_client_message("client-0", RequestStartGame())
    messages = [envelope.message for envelope in server.drain_outbox()]

    rejection = next(message for message in messages if isinstance(message, LobbyActionRejected))
    assert rejection.message == "could not start local bots"
    assert fake_server_handle.spawned[0].closed
    assert server.bot_manager.pending_display_names() == {1: "Bot_A", 2: "Bot_B"}
    assert not server.bot_manager.has_pending_starts
    assert server.active_match is None


def test_local_server_aborts_timed_out_start_and_removes_connected_start_bot() -> None:
    clock = _FakeClock(value=100.0)
    fake_server_handle = _FakeServerHandle()
    server = LocalServer(
        rng=random.Random(1234),
        seat_count=3,
        server_handle=fake_server_handle,
        bot_start_timeout_seconds=5.0,
        monotonic=clock,
    )
    _configure_human_and_two_bots(server)

    server.handle_client_message("client-0", RequestStartGame())
    first_name, first_client_id, _seed, first_handle = fake_server_handle.spawned[0]
    server.drain_outbox()
    server.handle_client_message(
        "temporary-bot-connection",
        JoinLobby(display_name=first_name, requested_client_id=first_client_id),
        reply_target_client_id="temporary-bot-connection",
    )
    server.drain_outbox()
    assert server.registry.has(first_client_id)

    clock.value = 105.0
    server.poll()
    envelopes = server.drain_outbox()

    rejection = next(
        envelope for envelope in envelopes if isinstance(envelope.message, LobbyActionRejected)
    )
    assert rejection.target_client_id == "client-0"
    assert "did not join within 5 seconds" in rejection.message.message
    assert not server.registry.has(first_client_id)
    assert first_handle.closed
    assert server.bot_manager.pending_display_names() == {1: "Bot_A", 2: "Bot_B"}
    assert not server.bot_manager.has_pending_starts
    assert server.active_match is None


def test_local_server_aborts_start_when_bot_process_exits_before_joining() -> None:
    clock = _FakeClock(value=100.0)
    fake_server_handle = _FakeServerHandle()
    server = LocalServer(
        rng=random.Random(1234),
        seat_count=2,
        server_handle=fake_server_handle,
        monotonic=clock,
    )
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message(
        "client-0", AssignSeatToClient(seat_index=0, target_client_id="client-0")
    )
    server.handle_client_message(
        "client-0", CreateLocalBotOnSeat(seat_index=1, display_name="Bot_A")
    )
    server.drain_outbox()

    server.handle_client_message("client-0", RequestStartGame())
    fake_server_handle.spawned[0][3].exit_code = 23
    server.drain_outbox()

    server.poll()
    messages = [envelope.message for envelope in server.drain_outbox()]

    rejection = next(message for message in messages if isinstance(message, LobbyActionRejected))
    assert "exit code 23" in rejection.message
    assert server.bot_manager.pending_display_names() == {1: "Bot_A"}
    assert not server.bot_manager.has_pending_starts
