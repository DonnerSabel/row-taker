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
from row_taker.engine.state import DeltaPublicState, GameState, PlayerState, PublicState
from row_taker.engine.views import build_player_state, build_public_state
from row_taker.hub.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ClientToHubMessage,
    HubToClientMessage,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


@dataclass(slots=True)
class MatchHub:
    state: GameState
    outbox: list[HubToClientMessage] = field(default_factory=list)
    _current_trick_public_state_before: PublicState | None = None
    _current_trick_deltas: list[DeltaPublicState] = field(default_factory=list)

    def start_match(self) -> None:
        self.outbox.append(StateUpdated(state=self.build_public_state()))
        self._request_choose_cards_for_current_trick()

    def handle_client_message(self, message: ClientToHubMessage) -> None:
        if isinstance(message, SubmitCard):
            self._handle_submit_card(message)
            return
        if isinstance(message, SubmitRowChoice):
            self._handle_submit_row_choice(message)
            return
        raise TypeError(f'unsupported client message type: {type(message)!r}')

    def drain_outbox(self) -> list[HubToClientMessage]:
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
        submit_play_card(self.state, message.command)
        if not all_cards_selected(self.state):
            return

        self._current_trick_public_state_before = self.build_public_state()
        self._current_trick_deltas.clear()
        begin_trick_resolution(self.state)
        self._advance_resolution_until_blocked()

    def _handle_submit_row_choice(self, message: SubmitRowChoice) -> None:
        delta = submit_choose_row(self.state, message.command)
        self._current_trick_deltas.append(delta)
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
                delta = resolve_next_delta_public_state(self.state)
                if delta is not None:
                    self._current_trick_deltas.append(delta)
                continue

            if trick_resolution_finished(self.state):
                self._finish_current_trick()
                return

            return

    def _finish_current_trick(self) -> None:
        public_state_before = self._current_trick_public_state_before
        if public_state_before is None:
            raise ValueError('missing public state before trick resolution')

        new_round_started = finish_trick(self.state)
        public_state_after = self.build_public_state()
        game_finished = self.is_finished()

        self.outbox.append(
            TrickResolved(
                public_state_before=public_state_before,
                deltas=list(self._current_trick_deltas),
                public_state_after=public_state_after,
                new_round_started=new_round_started,
                game_finished=game_finished,
            )
        )
        self.outbox.append(StateUpdated(state=public_state_after))

        self._current_trick_public_state_before = None
        self._current_trick_deltas.clear()

        if not game_finished:
            self._request_choose_cards_for_current_trick()
