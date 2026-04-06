from __future__ import annotations

import json

from row_taker.protocol.codec import (
    client_message_from_dict,
    client_message_to_dict,
    server_message_from_dict,
    server_message_to_dict,
)
from row_taker.protocol.messages import ClientToServerMessage, ServerToClientMessage


def encode_client_message(message: ClientToServerMessage) -> bytes:
    return (json.dumps(client_message_to_dict(message), separators=(",", ":")) + "\n").encode("utf-8")


def decode_client_message(data: bytes) -> ClientToServerMessage:
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"client payload must decode to dict, got {type(payload)!r}")
    return client_message_from_dict(payload)


def encode_server_message(message: ServerToClientMessage) -> bytes:
    return (json.dumps(server_message_to_dict(message), separators=(",", ":")) + "\n").encode("utf-8")


def decode_server_message(data: bytes) -> ServerToClientMessage:
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"server payload must decode to dict, got {type(payload)!r}")
    return server_message_from_dict(payload)
