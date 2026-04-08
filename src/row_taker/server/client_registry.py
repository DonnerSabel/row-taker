from __future__ import annotations

from dataclasses import dataclass, field

from row_taker.engine.lobby.config import ClientKind


@dataclass(slots=True, frozen=True)
class ConnectedClientRecord:
    client_id: str
    display_name: str
    kind: ClientKind


@dataclass(slots=True)
class ClientRegistry:
    records: dict[str, ConnectedClientRecord] = field(default_factory=dict)

    def add(self, client_id: str, display_name: str, kind: ClientKind) -> None:
        self.records[client_id] = ConnectedClientRecord(client_id=client_id, display_name=display_name, kind=kind)

    def remove(self, client_id: str) -> None:
        self.records.pop(client_id, None)

    def set_display_name(self, client_id: str, display_name: str) -> None:
        record = self.records[client_id]
        self.records[client_id] = ConnectedClientRecord(client_id=record.client_id, display_name=display_name, kind=record.kind)

    def get(self, client_id: str) -> ConnectedClientRecord:
        return self.records[client_id]

    def has(self, client_id: str) -> bool:
        return client_id in self.records

    def clients(self) -> tuple[ConnectedClientRecord, ...]:
        return tuple(self.records.values())
