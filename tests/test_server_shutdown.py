from __future__ import annotations

import random
from dataclasses import dataclass, field

import pytest

import row_taker.server.network_server as network_server_module
from row_taker.server.local_server import LocalServer
from row_taker.server.network_server import run_network_server


@dataclass
class _DummyBotHandle:
    close_calls: int = 0

    def poll(self) -> int | None:
        return None

    def close(self) -> None:
        self.close_calls += 1


@dataclass
class _FakeBotSpawner:
    handles: list[_DummyBotHandle] = field(default_factory=list)

    def spawn_local_bot(self, *, display_name: str, client_id: str, seed: int) -> _DummyBotHandle:
        del display_name, client_id, seed
        handle = _DummyBotHandle()
        self.handles.append(handle)
        return handle


class _ExplodingListener:
    def __enter__(self) -> _ExplodingListener:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def settimeout(self, timeout: float) -> None:
        del timeout

    def getsockname(self) -> tuple[str, int]:
        return ("127.0.0.1", 3000)

    def accept(self) -> tuple[object, object]:
        raise RuntimeError("accept failed")


@dataclass
class _FakeLocalServer:
    close_calls: int = 0

    @property
    def should_shutdown(self) -> bool:
        return False

    def poll(self) -> None:
        return None

    def drain_outbox(self) -> list[object]:
        return []

    def close(self) -> None:
        self.close_calls += 1


def test_local_server_close_closes_pending_bots_and_is_safe_twice() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    spawner = _FakeBotSpawner()
    server.bot_manager.reserve(0, "Bot_A")
    server.bot_manager.spawn_pending(
        spawner,
        client_id_in_use=lambda _client_id: False,
        started_at=0.0,
    )

    server.close()
    server.close()

    assert spawner.handles[0].close_calls == 1
    assert not server.bot_manager.has_pending_starts
    assert not server.bot_manager.has_running_bots


def test_network_server_closes_local_server_when_accept_loop_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_server = _FakeLocalServer()
    monkeypatch.setattr(
        network_server_module.socket,
        "create_server",
        lambda *_args, **_kwargs: _ExplodingListener(),
    )
    monkeypatch.setattr(
        network_server_module,
        "LocalServer",
        lambda **_kwargs: fake_server,
    )

    with pytest.raises(RuntimeError, match="accept failed"):
        run_network_server("127.0.0.1", 0)

    assert fake_server.close_calls == 1
