from __future__ import annotations

from dataclasses import dataclass

from row_taker.protocol.messages import ServerToClientMessage


@dataclass(slots=True, frozen=True)
class OutgoingEnvelope:
    message: ServerToClientMessage
    target_client_id: str | None = None
