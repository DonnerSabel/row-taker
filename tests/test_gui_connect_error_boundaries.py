from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

import row_taker.gui.app as app_module
from row_taker.gui.app import GuiApp
from row_taker.protocol.errors import ConnectionFailed


@dataclass
class _FakeTransport:
    closed: bool = False

    def close(self) -> None:
        self.closed = True


class _FailingLiveClient:
    error: Exception

    def __init__(self, transport: object, *, display_name: str) -> None:
        del transport, display_name

    def start(self) -> None:
        raise self.error


def _configure_connect_failure(
    monkeypatch: pytest.MonkeyPatch,
    transport: _FakeTransport,
    error: Exception,
) -> None:
    monkeypatch.setattr(
        app_module.ClientTransport,
        "connect",
        staticmethod(lambda host, port: transport),
    )
    _FailingLiveClient.error = error
    monkeypatch.setattr(app_module, "LiveGuiClient", _FailingLiveClient)


def test_expected_connect_failure_is_shown_and_transport_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _FakeTransport()
    _configure_connect_failure(
        monkeypatch,
        transport,
        ConnectionFailed("connection refused"),
    )
    app = GuiApp()

    app._attempt_connect()

    assert transport.closed
    assert app._connect_form.error_message == "Verbindung fehlgeschlagen: connection refused"
    assert app._live_client is None


def test_unexpected_connect_failure_is_logged_and_shown_generically(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _FakeTransport()
    _configure_connect_failure(
        monkeypatch,
        transport,
        RuntimeError("constructor bug"),
    )
    app = GuiApp()

    with caplog.at_level(logging.ERROR, logger="row_taker.gui.app"):
        app._attempt_connect()

    assert transport.closed
    assert app._connect_form.error_message == (
        "Unerwarteter Verbindungsfehler. Details stehen im Log."
    )
    assert "constructor bug" not in app._connect_form.error_message
    assert "constructor bug" in caplog.text
    assert app._live_client is None
