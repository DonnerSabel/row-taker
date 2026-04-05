from __future__ import annotations

from typing import Protocol

from row_taker.hub.messages import ClientToHubMessage, HubToClientMessage


class Client(Protocol):
    def handle_hub_message(self, message: HubToClientMessage) -> ClientToHubMessage | None:
        ...
