from __future__ import annotations

from dataclasses import dataclass, field

from row_taker.engine.game import (
    all_cards_selected,
    begin_trick_resolution,
    finish_trick,
    has_pending_resolution_step,
    has_pending_row_choice,
    resolve_next_delta_public_state,
    submit_choose_row,
    submit_play_card,
    trick_resolution_finished,
)
from row_taker.engine.models import PlayerID
from row_taker.engine.phases import Phase
from row_taker.engine.state import GameState, PlayerState, PublicState
from row_taker.engine.views import build_player_state, build_public_state
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    GameClientMessage,
    GameServerMessage,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


@dataclass(slots=True)
class MatchHub:
    state: GameState
    outbox: list[GameServerMessage] = field(default_factory=list)

    def start_match(self) -> None:
        self.outbox.append(StateUpdated(state=self.build_public_state()))
        self._request_choose_cards_for_current_trick()

    def handle_client_message(self, message: GameClientMessage) -> None:
        if isinstance(message, SubmitCard):
            self._handle_submit_card(message)
            return
        if isinstance(message, SubmitRowChoice):
            self._handle_submit_row_choice(message)
            return
        raise TypeError(f'unsupported client message type: {type(message)!r}')

    def drain_outbox(self) -> list[GameServerMessage]:
        drained = list(self.outbox)
        self.outbox.clear()
        return drained

    def is_finished(self) -> bool:
        return self.state.phase_info.phase == Phase.GAME_OVER

    def build_public_state(self) -> PublicState:
        return build_public_state(self.state)

    def build_player_state_for(self, player_id: PlayerID) -> PlayerState:
        return build_player_state(self.state, player_id)

    def _request_choose_cards_for_current_trick(self) -> None:
        for player in self.state.players:
            self.outbox.append(
                ChooseCardRequested(
                    player_id=player.player_id,
                    state=self.build_player_state_for(player.player_id),
                )
            )

    def _handle_submit_card(self, message: SubmitCard) -> None:
        submit_play_card(self.state, message.player_id, message.card_value)
        if not all_cards_selected(self.state):
            return

        begin_trick_resolution(self.state)
        self._advance_resolution_until_blocked()

    def _handle_submit_row_choice(self, message: SubmitRowChoice) -> None:
        submit_choose_row(self.state, message.player_id, message.row_id)
        self._advance_resolution_until_blocked()

    def _advance_resolution_until_blocked(self) -> None:
        while True:
            if has_pending_row_choice(self.state):
                active_player_id = self.state.phase_info.active_player_id
                if active_player_id is None:
                    raise ValueError('missing active_player_id for choose-row phase')
                self.outbox.append(
                    ChooseRowRequested(
                        player_id=active_player_id,
                        state=self.build_player_state_for(active_player_id),
                    )
                )
                return

            if has_pending_resolution_step(self.state):
                resolve_next_delta_public_state(self.state)
                continue

            if trick_resolution_finished(self.state):
                self._finish_current_trick()
                return

            return

    def _finish_current_trick(self) -> None:
        result = finish_trick(self.state)
        self.outbox.append(
            TrickResolved(
                deltas=result.deltas,
                new_round_started=result.new_round_started,
                game_finished=result.game_finished,
            )
        )
        public_state = self.build_public_state()
        self.outbox.append(StateUpdated(state=public_state))

        if not result.game_finished:
            self._request_choose_cards_for_current_trick()
