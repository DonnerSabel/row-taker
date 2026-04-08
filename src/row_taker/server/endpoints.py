from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from row_taker.protocol.messages import ClientToServerMessage, ServerToClientMessage


class ServerEndpoint(Protocol):
    def deliver(self, message: ServerToClientMessage) -> None:
        ...

    def drain_outgoing(self) -> list[ClientToServerMessage]:
        ...


class LocalEndpointRunner(Protocol):
    def pump(self) -> int:
        ...

    def close(self) -> None:
        ...


@dataclass(slots=True)
class LocalLoopbackEndpoint:
    incoming: list[ServerToClientMessage] = field(default_factory=list)
    outgoing: list[ClientToServerMessage] = field(default_factory=list)

    def deliver(self, message: ServerToClientMessage) -> None:
        self.incoming.append(message)

    def drain_incoming(self) -> list[ServerToClientMessage]:
        drained = list(self.incoming)
        self.incoming.clear()
        return drained

    def send_to_server(self, message: ClientToServerMessage) -> None:
        self.outgoing.append(message)

    def drain_outgoing(self) -> list[ClientToServerMessage]:
        drained = list(self.outgoing)
        self.outgoing.clear()
        return drained
