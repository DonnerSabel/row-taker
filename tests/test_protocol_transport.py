from __future__ import annotations

import socket

import pytest

from row_taker.protocol.errors import ConnectionClosed, MessageDecodeError
from row_taker.protocol.messages import IdentityAssigned, JoinLobby, LobbyActionRejected
from row_taker.protocol.transport import ClientTransport, ServerTransport, TcpLineTransport


def _pair() -> tuple[ClientTransport, ServerTransport]:
    left, right = socket.socketpair()
    return (
        ClientTransport(TcpLineTransport.from_socket(left)),
        ServerTransport(TcpLineTransport.from_socket(right)),
    )


def test_client_to_server_roundtrip() -> None:
    client, server = _pair()
    try:
        client.send(JoinLobby(display_name="Alice"))
        assert server.receive() == JoinLobby(display_name="Alice")
    finally:
        client.close()
        server.close()


def test_server_to_client_roundtrip() -> None:
    client, server = _pair()
    try:
        server.send(LobbyActionRejected(message="nein"))
        assert client.receive() == LobbyActionRejected(message="nein")
    finally:
        client.close()
        server.close()


def test_identity_assigned_roundtrip() -> None:
    client, server = _pair()
    try:
        server.send(IdentityAssigned(client_id="client-7"))
        assert client.receive() == IdentityAssigned(client_id="client-7")
    finally:
        client.close()
        server.close()


def test_receive_raises_connection_closed_on_eof() -> None:
    client, server = _pair()
    try:
        server.close()
        with pytest.raises(ConnectionClosed):
            client.receive()
    finally:
        client.close()


def test_receive_raises_message_decode_error_on_invalid_json() -> None:
    left, right = socket.socketpair()
    client = ClientTransport(TcpLineTransport.from_socket(left))
    try:
        right.sendall(b"not-json\n")
        with pytest.raises(MessageDecodeError):
            client.receive()
    finally:
        client.close()
        right.close()


def test_close_is_idempotent_and_exposes_closed_socket_state() -> None:
    left, right = socket.socketpair()
    transport = ClientTransport(TcpLineTransport.from_socket(left))
    try:
        transport.close()
        transport.close()
        with pytest.raises(ConnectionClosed):
            _ = transport.sock
    finally:
        right.close()


def test_closed_line_transport_rejects_send_and_receive() -> None:
    left, right = socket.socketpair()
    line_transport = TcpLineTransport.from_socket(left)
    try:
        line_transport.close()
        with pytest.raises(ConnectionClosed):
            line_transport.send_line(b"hello\n")
        with pytest.raises(ConnectionClosed):
            line_transport.receive_line()
    finally:
        right.close()
