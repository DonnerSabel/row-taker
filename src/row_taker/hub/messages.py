from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.models import PlayerID
from row_taker.engine.state import DeltaPublicState, PlayerState, PublicState


@dataclass(frozen=True, slots=True)
class SubmitCard:
    command: PlayCardCommand


@dataclass(frozen=True, slots=True)
class SubmitRowChoice:
    command: ChooseRowCommand


ClientToHubMessage = SubmitCard | SubmitRowChoice


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
    deltas: list[DeltaPublicState]
    public_state_after: PublicState
    new_round_started: bool
    game_finished: bool


HubToClientMessage = StateUpdated | ChooseCardRequested | ChooseRowRequested | TrickResolved
