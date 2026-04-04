from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.game import StepResult, resolve_round, start_next_round_if_needed
from row_taker.engine.models import PlayerID
from row_taker.engine.state import GameState, PlayerState
from row_taker.engine.views import build_player_state
from row_taker.hub.hub_participant import HubParticipant


@dataclass(slots=True)
class TrickResult:
    public_state_before: PlayerState
    resolution: list[StepResult]
    public_state_after: PlayerState
    new_round_started: bool
    game_finished: bool


@dataclass(slots=True)
class MatchHub:
    state: GameState
    participants_by_player_id: dict[PlayerID, HubParticipant]

    def play_trick(self) -> TrickResult:
        selections = self._collect_card_selections()
        public_state_before = self.build_public_player_state()

        results = resolve_round(
            self.state,
            selections,
            lambda current_state, player_id, played_card: self._request_row_choice_for_player(player_id),
        )

        new_round_started = start_next_round_if_needed(self.state)

        return TrickResult(
            public_state_before=public_state_before,
            resolution=results,
            public_state_after=self.build_public_player_state(),
            new_round_started=new_round_started,
            game_finished=self.is_finished(),
        )

    def is_finished(self) -> bool:
        return self.state.phase_info.phase == 'game_over'

    def build_public_player_state(self) -> PlayerState:
        return build_player_state(self.state, self.state.players[0].player_id)

    def build_player_state_for(self, player_id: PlayerID) -> PlayerState:
        return build_player_state(self.state, player_id)

    def _collect_card_selections(self) -> dict[PlayerID, PlayCardCommand]:
        selections: dict[PlayerID, PlayCardCommand] = {}
        for player in self.state.players:
            player_state = self.build_player_state_for(player.player_id)
            participant = self.participants_by_player_id[player.player_id]
            selections[player.player_id] = participant.on_choose_card_request(player_state)
        return selections

    def _request_row_choice_for_player(self, player_id: PlayerID) -> ChooseRowCommand:
        player_state = self.build_player_state_for(player_id)
        participant = self.participants_by_player_id[player_id]
        return participant.on_choose_row_request(player_state)
