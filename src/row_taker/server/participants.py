from __future__ import annotations

from dataclasses import dataclass

from row_taker.participants import ParticipantKind, ParticipantLocation


@dataclass(slots=True, frozen=True)
class Participant:
    client_id: str
    display_name: str
    kind: ParticipantKind
    location: ParticipantLocation
    endpoint_display: str | None = None
