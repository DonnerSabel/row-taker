from __future__ import annotations

from enum import StrEnum


class ParticipantKind(StrEnum):
    HUMAN = "human"
    BOT = "bot"


class ParticipantLocation(StrEnum):
    LOCAL = "local"
    REMOTE = "remote"
