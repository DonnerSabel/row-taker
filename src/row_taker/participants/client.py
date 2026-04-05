from __future__ import annotations

from typing import Protocol

from row_taker.hub.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


HubMessage = StateUpdated | ChooseCardRequested | ChooseRowRequested | TrickResolved
ClientMessage = SubmitCard | SubmitRowChoice


class Client(Protocol):
    def handle_hub_message(self, message: HubMessage) -> list[ClientMessage]:
        ...
