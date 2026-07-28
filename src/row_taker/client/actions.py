from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.models import RowID


class ClientAction:
    pass


@dataclass(frozen=True, slots=True)
class ClientActionRename(ClientAction):
    name: str


@dataclass(frozen=True, slots=True)
class ClientActionAssignSelfToSeat(ClientAction):
    seat_index: int


@dataclass(frozen=True, slots=True)
class ClientActionCreateBot(ClientAction):
    seat_index: int
    name: str


@dataclass(frozen=True, slots=True)
class ClientActionClearSeat(ClientAction):
    seat_index: int


@dataclass(frozen=True, slots=True)
class ClientActionStartGame(ClientAction):
    pass


@dataclass(frozen=True, slots=True)
class ClientActionChooseCard(ClientAction):
    card_value: int


@dataclass(frozen=True, slots=True)
class ClientActionChooseRow(ClientAction):
    row_id: RowID


@dataclass(frozen=True, slots=True)
class ClientActionLeaveSession(ClientAction):
    pass


@dataclass(frozen=True, slots=True)
class ClientActionAdvancePresentation(ClientAction):
    pass
