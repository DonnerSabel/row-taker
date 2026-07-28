from __future__ import annotations

import json

from row_taker.protocol.codec import (
    client_message_from_dict,
    client_message_to_dict,
    server_message_from_dict,
    server_message_to_dict,
)
from row_taker.protocol.errors import MessageDecodeError, MessageEncodeError
from row_taker.protocol.messages import ClientToServerMessage, ServerToClientMessage
from row_taker.serialization.json_values import require_object


def encode_client_message(message: ClientToServerMessage) -> bytes:
    try:
        payload = client_message_to_dict(message)
        return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise MessageEncodeError(str(exc)) from exc


def decode_client_message(data: bytes) -> ClientToServerMessage:
    try:
        raw_payload: object = json.loads(data.decode("utf-8"))
        payload = require_object(raw_payload, context="client payload")
        return client_message_from_dict(payload)
    except MessageDecodeError:
        raise
    except Exception as exc:
        raise MessageDecodeError(str(exc)) from exc


def encode_server_message(message: ServerToClientMessage) -> bytes:
    try:
        payload = server_message_to_dict(message)
        return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise MessageEncodeError(str(exc)) from exc


def decode_server_message(data: bytes) -> ServerToClientMessage:
    try:
        raw_payload: object = json.loads(data.decode("utf-8"))
        payload = require_object(raw_payload, context="server payload")
        return server_message_from_dict(payload)
    except MessageDecodeError:
        raise
    except Exception as exc:
        raise MessageDecodeError(str(exc)) from exc
