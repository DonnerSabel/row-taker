from __future__ import annotations

import asyncio

from row_taker.cli.client_session import ClientSession
from row_taker.protocol.messages import SessionEnded, SessionEndReason


class _FakeConsole:
    instances: list["_FakeConsole"] = []

    def __init__(self) -> None:
        self.renders: list[tuple[str, str | None]] = []
        self.closed = False
        type(self).instances.append(self)

    async def render(self, screen: str, prompt: str | None) -> None:
        self.renders.append((screen, prompt))

    async def read_line(self) -> str:
        await asyncio.Future()
        raise AssertionError("unreachable")

    async def close(self) -> None:
        self.closed = True


class _FakeTransport:
    def __init__(self) -> None:
        self.closed = False

    def receive(self) -> SessionEnded:
        return SessionEnded(
            message="Spiel abgebrochen: Hugo hat die Sitzung verlassen.",
            reason=SessionEndReason.QUIT,
            client_id="client-1",
            display_name="Hugo",
        )

    def send(self, _message: object) -> None:
        raise AssertionError("send() should not be called in this test")

    def close(self) -> None:
        self.closed = True


def test_session_ended_clears_prompt_before_shutdown(monkeypatch) -> None:
    monkeypatch.setattr("row_taker.cli.client_session.CliConsole", _FakeConsole)
    transport = _FakeTransport()
    session = ClientSession(transport=transport)

    result = asyncio.run(session.run_async())

    assert result is None
    assert transport.closed is True
    console = _FakeConsole.instances[-1]
    assert console.closed is True
    assert console.renders[-1][1] is None
    assert "Spiel abgebrochen" in console.renders[-1][0]
