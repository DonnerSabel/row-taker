from __future__ import annotations

import random
from dataclasses import dataclass, field

import pytest

from row_taker.engine.lobby.rules import assign_client_to_seat
from row_taker.engine.lobby.state import LobbyState
from row_taker.server.local_bot_manager import LocalBotManager


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

    def spawn_local_bot(
        self,
        *,
        display_name: str,
        client_id: str,
        seed: int,
    ) -> _DummyHandle:
        handle = _DummyHandle()
        self.spawned.append((display_name, client_id, seed, handle))
        return handle


def test_reservations_supply_lobby_overlay_and_can_be_cleared() -> None:
    manager = LocalBotManager(rng=random.Random(1234))

    manager.reserve(1, "Bot_Bob")

    assert manager.pending_display_names() == {1: "Bot_Bob"}
    assert manager.has_pending_reservations

    manager.clear_reservation(1)

    assert manager.pending_display_names() == {}
    assert not manager.has_pending_reservations


def test_pending_bots_complete_a_partially_human_lobby() -> None:
    manager = LocalBotManager(rng=random.Random(1234))
    lobby = assign_client_to_seat(LobbyState(seat_count=2), "client-0", 0)

    assert not manager.can_complete_lobby(lobby)

    manager.reserve(1, "Bot_Bob")

    assert manager.can_complete_lobby(lobby)


def test_spawn_adopt_and_close_running_bot() -> None:
    manager = LocalBotManager(rng=random.Random(1234))
    server_handle = _FakeServerHandle()
    manager.reserve(1, "Bot_Bob")

    started = manager.spawn_pending(
        server_handle,
        client_id_in_use=lambda client_id: client_id == "bot-1",
        started_at=10.0,
    )

    assert [pending.client_id for pending in started] == ["bot-2"]
    assert manager.has_pending_starts
    pending = manager.pending_start("bot-2")
    assert pending is not None

    adopted = manager.mark_connected("bot-2")

    assert adopted is pending
    assert not manager.has_pending_starts
    assert manager.has_running_bots
    assert manager.pending_display_names() == {}

    manager.close_running("bot-2")

    assert server_handle.spawned[0][3].closed
    assert not manager.has_running_bots


def test_abort_startup_closes_all_pending_processes() -> None:
    manager = LocalBotManager(rng=random.Random(1234))
    server_handle = _FakeServerHandle()
    manager.reserve(0, "Bot_A")
    manager.reserve(1, "Bot_B")
    manager.spawn_pending(
        server_handle,
        client_id_in_use=lambda _client_id: False,
        started_at=10.0,
    )

    manager.abort_startup()

    assert all(handle.closed for *_prefix, handle in server_handle.spawned)
    assert not manager.has_pending_starts


def test_duplicate_reservation_name_is_rejected_but_same_seat_can_keep_it() -> None:
    from row_taker.server.errors import ClientRequestRejected

    manager = LocalBotManager(rng=random.Random(1234))
    manager.reserve(0, "Bot_A")

    same_seat = manager.reserve(0, " bot_a ")
    assert same_seat.display_name == "bot_a"

    with pytest.raises(ClientRequestRejected, match="duplicate participant display name"):
        manager.reserve(1, "BOT_A")


def test_clearing_reservation_releases_display_name() -> None:
    manager = LocalBotManager(rng=random.Random(1234))
    manager.reserve(0, "Bot_A")
    manager.clear_reservation(0)

    spec = manager.reserve(1, "Bot_A")
    assert spec.display_name == "Bot_A"


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


def test_spawn_pending_rolls_back_processes_when_later_spawn_fails() -> None:
    from row_taker.server.local_bot_manager import BotSpawnError

    manager = LocalBotManager(rng=random.Random(1234))
    server_handle = _FailingServerHandle(fail_on_call=2)
    manager.reserve(0, "Bot_A")
    manager.reserve(1, "Bot_B")

    with pytest.raises(BotSpawnError, match="could not spawn all local bot processes"):
        manager.spawn_pending(
            server_handle,
            client_id_in_use=lambda _client_id: False,
            started_at=10.0,
        )

    assert server_handle.spawned[0].closed
    assert not manager.has_pending_starts
    assert not manager.has_running_bots
    assert manager.pending_display_names() == {0: "Bot_A", 1: "Bot_B"}


def test_startup_failure_reports_early_process_exit_and_timeout() -> None:
    manager = LocalBotManager(rng=random.Random(1234))
    server_handle = _FakeServerHandle()
    manager.reserve(0, "Bot_A")
    manager.spawn_pending(
        server_handle,
        client_id_in_use=lambda _client_id: False,
        started_at=10.0,
    )
    handle = server_handle.spawned[0][3]

    assert manager.startup_failure(now=14.9, timeout_seconds=5.0) is None

    timeout = manager.startup_failure(now=15.0, timeout_seconds=5.0)
    assert timeout is not None
    assert "did not join within 5 seconds" in timeout.message

    handle.exit_code = 17
    exited = manager.startup_failure(now=11.0, timeout_seconds=5.0)
    assert exited is not None
    assert "exit code 17" in exited.message


def test_abort_startup_restores_connected_bot_reservations() -> None:
    manager = LocalBotManager(rng=random.Random(1234))
    server_handle = _FakeServerHandle()
    manager.reserve(0, "Bot_A")
    manager.reserve(1, "Bot_B")
    starts = manager.spawn_pending(
        server_handle,
        client_id_in_use=lambda _client_id: False,
        started_at=10.0,
    )

    manager.mark_connected(starts[0].client_id)
    aborted_client_ids = manager.abort_startup()

    assert aborted_client_ids == tuple(start.client_id for start in starts)
    assert all(handle.closed for *_prefix, handle in server_handle.spawned)
    assert manager.pending_display_names() == {0: "Bot_A", 1: "Bot_B"}
    assert not manager.has_pending_starts
    assert not manager.has_running_bots
