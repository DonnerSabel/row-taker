from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class ConnectedClientRecord:
    client_id: str
    display_name: str
    seat_index: int | None = None


@dataclass(slots=True)
class ClientRegistry:
    records: dict[str, ConnectedClientRecord] = field(default_factory=dict)

    def add(self, client_id: str, display_name: str) -> None:
        self.records[client_id] = ConnectedClientRecord(client_id=client_id, display_name=display_name)

    def remove(self, client_id: str) -> None:
        self.records.pop(client_id, None)

    def set_display_name(self, client_id: str, display_name: str) -> None:
        record = self.records[client_id]
        self.records[client_id] = ConnectedClientRecord(client_id=record.client_id, display_name=display_name, seat_index=record.seat_index)

    def set_seat(self, client_id: str, seat_index: int | None) -> None:
        record = self.records[client_id]
        self.records[client_id] = ConnectedClientRecord(client_id=record.client_id, display_name=record.display_name, seat_index=seat_index)

    def clients(self) -> tuple[ConnectedClientRecord, ...]:
        return tuple(self.records.values())
