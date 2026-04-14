from __future__ import annotations

from dataclasses import dataclass

from row_taker.client.state import ClientState
from row_taker.protocol.messages import ClientToServerMessage, ServerToClientMessage


@dataclass(frozen=True, slots=True)
class CoreUpdate:
    state: ClientState
    applied_server_messages: tuple[ServerToClientMessage, ...] = ()
    outbound_messages: tuple[ClientToServerMessage, ...] = ()
    local_messages: tuple[str, ...] = ()
