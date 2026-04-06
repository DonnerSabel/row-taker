from __future__ import annotations

from typing import Protocol

from row_taker.protocol.messages import ClientToServerMessage, ServerToClientMessage


class Client(Protocol):
    def handle_server_message(self, message: ServerToClientMessage) -> ClientToServerMessage | None:
        ...
