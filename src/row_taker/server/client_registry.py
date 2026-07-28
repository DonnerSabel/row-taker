from __future__ import annotations

from dataclasses import dataclass, field

from row_taker.server.errors import ClientRequestRejected
from row_taker.server.participants import Participant


@dataclass(slots=True)
class ClientRegistry:
    _participants_by_client_id: dict[str, Participant] = field(default_factory=dict)

    def register_participant(self, participant: Participant) -> None:
        self.validate_display_name(
            participant.display_name,
            exclude_client_id=participant.client_id,
        )
        self._participants_by_client_id[participant.client_id] = participant

    def remove_participant(self, client_id: str) -> None:
        self._participants_by_client_id.pop(client_id, None)

    def set_display_name(self, client_id: str, display_name: str) -> None:
        participant = self.get_participant(client_id)
        value = self.validate_display_name(display_name, exclude_client_id=client_id)
        self._participants_by_client_id[client_id] = Participant(
            client_id=participant.client_id,
            display_name=value,
            kind=participant.kind,
            location=participant.location,
            endpoint_display=participant.endpoint_display,
        )

    def get_participant(self, client_id: str) -> Participant:
        return self._participants_by_client_id[client_id]

    def list_participants(self) -> tuple[Participant, ...]:
        return tuple(self._participants_by_client_id.values())

    def client_ids(self) -> tuple[str, ...]:
        return tuple(self._participants_by_client_id)

    @property
    def is_empty(self) -> bool:
        return not self._participants_by_client_id

    def has(self, client_id: str) -> bool:
        return client_id in self._participants_by_client_id

    def validate_display_name(
        self,
        display_name: str,
        *,
        exclude_client_id: str | None = None,
    ) -> str:
        value = display_name.strip()
        if not value:
            raise ClientRequestRejected("display name must not be empty")
        normalized = value.casefold()
        for existing_client_id, participant in self._participants_by_client_id.items():
            if exclude_client_id is not None and existing_client_id == exclude_client_id:
                continue
            if participant.display_name.strip().casefold() == normalized:
                raise ClientRequestRejected(f"duplicate participant display name: {value!r}")
        return value
