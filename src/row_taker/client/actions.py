from __future__ import annotations

from dataclasses import dataclass


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
    row_id: object


@dataclass(frozen=True, slots=True)
class UiActionLeaveSession(UiAction):
    pass


@dataclass(frozen=True, slots=True)
class UiActionAdvancePresentation(UiAction):
    pass
