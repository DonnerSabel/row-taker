from __future__ import annotations

from dataclasses import dataclass, field

from row_taker.server.errors import ClientRequestRejected
from row_taker.server.participants import Participant


@dataclass(slots=True, frozen=True)
class RegistryEntry:
    participant: Participant


@dataclass(slots=True)
class ClientRegistry:
    records: dict[str, RegistryEntry] = field(default_factory=dict)

    def register_participant(self, participant: Participant) -> None:
        self._validate_display_name(
            participant.display_name, exclude_client_id=participant.client_id
        )
        self.records[participant.client_id] = RegistryEntry(participant=participant)

    def remove_participant(self, client_id: str) -> None:
        self.records.pop(client_id, None)

    def set_display_name(self, client_id: str, display_name: str) -> None:
        participant = self.get_participant(client_id)
        self._validate_display_name(display_name, exclude_client_id=client_id)
        self.records[client_id] = RegistryEntry(
            participant=Participant(
                client_id=participant.client_id,
                display_name=display_name.strip(),
                kind=participant.kind,
                location=participant.location,
                endpoint_display=participant.endpoint_display,
            ),
        )

    def get_participant(self, client_id: str) -> Participant:
        return self.records[client_id].participant

    def list_participants(self) -> tuple[Participant, ...]:
        return tuple(entry.participant for entry in self.records.values())

    def has(self, client_id: str) -> bool:
        return client_id in self.records

    def _validate_display_name(
        self, display_name: str, exclude_client_id: str | None = None
    ) -> str:
        value = display_name.strip()
        if not value:
            raise ClientRequestRejected("display name must not be empty")
        normalized = value.casefold()
        for existing_client_id, entry in self.records.items():
            if exclude_client_id is not None and existing_client_id == exclude_client_id:
                continue
            if entry.participant.display_name.strip().casefold() == normalized:
                raise ClientRequestRejected(f"duplicate participant display name: {value!r}")
        return value
