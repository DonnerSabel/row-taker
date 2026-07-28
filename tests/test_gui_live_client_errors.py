from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pytest

from row_taker.client.update import CoreUpdate
from row_taker.gui.live_client import LiveGuiClient
from row_taker.protocol.errors import ReceiveFailed, SendFailed
from row_taker.protocol.messages import JoinLobby


@dataclass
class _FakeTransport:
    send_error: Exception | None = None
    receive_error: Exception | None = None
    sent: list[object] = field(default_factory=list)
    closed: bool = False

    def send(self, message: object) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent.append(message)

    def receive(self) -> object:
        if self.receive_error is None:
            raise AssertionError("receive result not configured")
        raise self.receive_error

    def close(self) -> None:
        self.closed = True


def test_expected_send_failure_becomes_user_message_without_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _FakeTransport(send_error=SendFailed("socket closed"))
    client = LiveGuiClient(transport, display_name="Alice")  # type: ignore[arg-type]

    with caplog.at_level(logging.INFO, logger="row_taker.gui.live_client"):
        client._apply_update(
            CoreUpdate(
                state=client.state,
                outbound_messages=(JoinLobby(display_name="Alice"),),
            )
        )

    assert client.state.flash_message is not None
    assert client.state.flash_message.text == "Senden an den Server fehlgeschlagen."
    assert "sending to server failed" in caplog.text
    assert "Traceback" not in caplog.text


def test_unexpected_send_failure_is_logged_and_shown_generically(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _FakeTransport(send_error=RuntimeError("programming error"))
    client = LiveGuiClient(transport, display_name="Alice")  # type: ignore[arg-type]

    with caplog.at_level(logging.ERROR, logger="row_taker.gui.live_client"):
        client._apply_update(
            CoreUpdate(
                state=client.state,
                outbound_messages=(JoinLobby(display_name="Alice"),),
            )
        )

    assert client.state.flash_message is not None
    assert "Unerwarteter Fehler" in client.state.flash_message.text
    assert "programming error" not in client.state.flash_message.text
    assert "programming error" in caplog.text


def test_expected_receive_failure_is_reported_as_network_error() -> None:
    transport = _FakeTransport(receive_error=ReceiveFailed("connection reset"))
    client = LiveGuiClient(transport, display_name="Alice")  # type: ignore[arg-type]

    client._receive_loop()
    client.poll()

    assert client.state.session_error == "Netzwerkfehler: connection reset"


def test_unexpected_receive_failure_is_logged_and_reported_generically(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _FakeTransport(receive_error=RuntimeError("decoder bug"))
    client = LiveGuiClient(transport, display_name="Alice")  # type: ignore[arg-type]

    with caplog.at_level(logging.ERROR, logger="row_taker.gui.live_client"):
        client._receive_loop()
    client.poll()

    assert client.state.session_error == (
        "Unerwarteter Netzwerkfehler. Details stehen im Log."
    )
    assert "decoder bug" in caplog.text
