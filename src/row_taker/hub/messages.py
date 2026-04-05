from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.state import PlayerState, PublicState
from row_taker.engine.game import StepResult
from row_taker.engine.models import PlayerID, RowID


@dataclass(frozen=True, slots=True)
class SubmitCard:
    player_id: PlayerID
    card_value: int


@dataclass(frozen=True, slots=True)
class SubmitRowChoice:
    player_id: PlayerID
    row_id: RowID


@dataclass(frozen=True, slots=True)
class StateUpdated:
    state: PublicState


@dataclass(frozen=True, slots=True)
class ChooseCardRequested:
    player_id: PlayerID
    state: PlayerState


@dataclass(frozen=True, slots=True)
class ChooseRowRequested:
    player_id: PlayerID
    state: PlayerState


@dataclass(frozen=True, slots=True)
class TrickResolved:
    public_state_before: PublicState
    resolution: list[StepResult]
    public_state_after: PublicState
    new_round_started: bool
    game_finished: bool
