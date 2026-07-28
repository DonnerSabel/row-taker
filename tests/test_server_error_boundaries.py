from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

import pytest

from row_taker.protocol.messages import (
    AssignSeatToClient,
    JoinLobby,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    SetDisplayName,
    SubmitCard,
)
from row_taker.server.local_server import LocalServer
from row_taker.server.network_server import _serve_connection


def test_expected_client_request_error_is_reported_and_lobby_is_resent() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.drain_outbox()

    server.handle_client_message(
        "client-0",
        AssignSeatToClient(seat_index=99, target_client_id="client-0"),
    )
    envelopes = server.drain_outbox()

    assert isinstance(envelopes[0].message, LobbyActionRejected)
    assert "seat index out of range" in envelopes[0].message.message
    assert envelopes[0].target_client_id == "client-0"
    assert isinstance(envelopes[1].message, LobbyStateUpdated)
    assert envelopes[1].target_client_id == "client-0"



def test_invalid_game_action_is_rejected_without_lobby_snapshot() -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.handle_client_message("client-1", JoinLobby(display_name="Bob"))
    server.handle_client_message(
        "client-0",
        AssignSeatToClient(seat_index=0, target_client_id="client-0"),
    )
    server.handle_client_message(
        "client-1",
        AssignSeatToClient(seat_index=1, target_client_id="client-1"),
    )
    server.drain_outbox()
    server.handle_client_message("client-0", RequestStartGame())
    server.drain_outbox()

    server.handle_client_message("client-0", SubmitCard(card_value=999))
    envelopes = server.drain_outbox()

    assert len(envelopes) == 1
    assert isinstance(envelopes[0].message, LobbyActionRejected)
    assert "invalid card value" in envelopes[0].message.message
    assert envelopes[0].target_client_id == "client-0"
    assert server.active_match is not None
    assert server.active_match.state.selected_cards == {}

def test_unexpected_local_server_error_is_not_disguised_as_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = LocalServer(rng=random.Random(1234), seat_count=2)
    server.handle_client_message("client-0", JoinLobby(display_name="Alice"))
    server.drain_outbox()

    def fail_unexpectedly(
        self: LocalServer,
        client_id: str,
        message: SetDisplayName,
    ) -> None:
        del self, client_id, message
        raise RuntimeError("programming error")

    monkeypatch.setattr(LocalServer, "_handle_set_display_name", fail_unexpectedly)

    with pytest.raises(RuntimeError, match="programming error"):
        server.handle_client_message(
            "client-0",
            SetDisplayName(display_name="Alicia"),
        )

    assert server.drain_outbox() == []


@dataclass
class _ReceiveOnceTransport:
    message: object

    def receive(self) -> object:
        return self.message


@dataclass
class _ExplodingNetworkServer:
    removed_client_ids: list[str] = field(default_factory=list)

    def add_connection(self, transport: object, endpoint_display: str | None = None) -> str:
        del transport, endpoint_display
        return "client-0"

    def handle_client_message(self, client_id: str, message: object) -> str:
        del client_id, message
        raise RuntimeError("unexpected server failure")

    def remove_connection(self, client_id: str) -> None:
        self.removed_client_ids.append(client_id)


def test_network_connection_boundary_logs_unexpected_server_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = _ReceiveOnceTransport(JoinLobby(display_name="Alice"))
    network_server = _ExplodingNetworkServer()
    monkeypatch.setattr(
        "row_taker.server.network_server.ServerTransport.from_socket",
        lambda conn: transport,
    )

    with caplog.at_level(logging.ERROR, logger="row_taker.server.network"):
        _serve_connection(object(), network_server, "test-endpoint")  # type: ignore[arg-type]

    assert network_server.removed_client_ids == ["client-0"]
    assert "unexpected server error" in caplog.text
    assert "unexpected server failure" in caplog.text
