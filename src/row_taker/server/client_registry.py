from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from row_taker.server.participants import Participant

if TYPE_CHECKING:
    from row_taker.server.endpoints import LocalEndpointRunner, ServerEndpoint


@dataclass(slots=True, frozen=True)
class RegistryEntry:
    participant: Participant
    endpoint: ServerEndpoint | None = None
    runner: LocalEndpointRunner | None = None


@dataclass(slots=True)
class ClientRegistry:
    records: dict[str, RegistryEntry] = field(default_factory=dict)

    def register_participant(
        self,
        participant: Participant,
        endpoint: ServerEndpoint | None = None,
        runner: LocalEndpointRunner | None = None,
    ) -> None:
        self._validate_display_name(participant.display_name, exclude_client_id=participant.client_id)
        self.records[participant.client_id] = RegistryEntry(
            participant=participant,
            endpoint=endpoint,
            runner=runner,
        )

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
            ),
            endpoint=self.get_endpoint(client_id),
            runner=self.get_runner(client_id),
        )

    def get_participant(self, client_id: str) -> Participant:
        return self.records[client_id].participant

    def get_endpoint(self, client_id: str) -> ServerEndpoint | None:
        return self.records[client_id].endpoint

    def get_runner(self, client_id: str) -> LocalEndpointRunner | None:
        return self.records[client_id].runner

    def list_participants(self) -> tuple[Participant, ...]:
        return tuple(entry.participant for entry in self.records.values())

    def has(self, client_id: str) -> bool:
        return client_id in self.records

    def _validate_display_name(self, display_name: str, exclude_client_id: str | None = None) -> str:
        value = display_name.strip()
        if not value:
            raise ValueError('display name must not be empty')
        normalized = value.casefold()
        for existing_client_id, entry in self.records.items():
            if exclude_client_id is not None and existing_client_id == exclude_client_id:
                continue
            if entry.participant.display_name.strip().casefold() == normalized:
                raise ValueError(f'duplicate participant display name: {value!r}')
        return value
