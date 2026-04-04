from __future__ import annotations

from typing import Protocol

from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.state import PlayerState


class HubParticipant(Protocol):
    def on_choose_card_request(self, state: PlayerState) -> PlayCardCommand:
        ...

    def on_choose_row_request(self, state: PlayerState) -> ChooseRowCommand:
        ...
