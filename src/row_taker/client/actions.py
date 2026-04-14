from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.game.models import RowID


@dataclass(frozen=True, slots=True)
class UiAction:
    pass


@dataclass(frozen=True, slots=True)
class UiActionRename(UiAction):
    name: str


@dataclass(frozen=True, slots=True)
class UiActionAssignSelfToSeat(UiAction):
    seat_index: int


@dataclass(frozen=True, slots=True)
class UiActionCreateBot(UiAction):
    seat_index: int
    name: str


@dataclass(frozen=True, slots=True)
class UiActionClearSeat(UiAction):
    seat_index: int


@dataclass(frozen=True, slots=True)
class UiActionStartGame(UiAction):
    pass


@dataclass(frozen=True, slots=True)
class UiActionChooseCard(UiAction):
    card_value: int


@dataclass(frozen=True, slots=True)
class UiActionChooseRow(UiAction):
    row_id: RowID


@dataclass(frozen=True, slots=True)
class UiActionLeaveSession(UiAction):
    pass


@dataclass(frozen=True, slots=True)
class UiActionAdvancePresentation(UiAction):
    pass
