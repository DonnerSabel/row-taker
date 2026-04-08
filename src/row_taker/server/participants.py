from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ParticipantKind(str, Enum):
    HUMAN = 'human'
    BOT = 'bot'


class ParticipantLocation(str, Enum):
    LOCAL = 'local'
    REMOTE = 'remote'


@dataclass(slots=True, frozen=True)
class Participant:
    client_id: str
    display_name: str
    kind: ParticipantKind
    location: ParticipantLocation
