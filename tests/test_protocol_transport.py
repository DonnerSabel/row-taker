from __future__ import annotations

import socket

import pytest

from row_taker.protocol.errors import ConnectionClosed, MessageDecodeError
from row_taker.protocol.messages import JoinLobby, LobbyActionRejected
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
