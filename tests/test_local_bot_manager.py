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

    started = manager.spawn_pending(  # type: ignore[arg-type]
        server_handle,
        client_id_in_use=lambda client_id: client_id == "bot-1",
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
    manager.spawn_pending(  # type: ignore[arg-type]
        server_handle,
        client_id_in_use=lambda _client_id: False,
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
