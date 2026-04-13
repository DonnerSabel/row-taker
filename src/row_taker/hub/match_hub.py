from __future__ import annotations

from dataclasses import dataclass, field

from row_taker.engine.game import (
    all_cards_selected,
    begin_trick_resolution,
    current_revealed_plays,
    finish_trick,
    has_pending_resolution_step,
    has_pending_row_choice,
    resolve_next_trick_step,
    submit_choose_row,
    submit_play_card,
    trick_resolution_finished,
)
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.phases import Phase
from row_taker.engine.game.state import GameState, PlayerState, PublicState, RevealedPlay, RowChoiceRequired, TrickResolutionStep
from row_taker.engine.game.views import build_player_state, build_public_state
from row_taker.protocol.messages import (
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    GameClientMessage,
    GameServerMessage,
    PlayedCardView,
    RowChoiceCommitted,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
)


@dataclass(slots=True)
class MatchHub:
    state: GameState
    outbox: list[GameServerMessage] = field(default_factory=list)

    def start_match(self) -> None:
        self.outbox.append(StateUpdated(state=self.build_public_state()))
        self._request_choose_cards_for_current_trick()

    def handle_client_message(self, player_id: PlayerID, message: GameClientMessage) -> None:
        if isinstance(message, SubmitCard):
            self._handle_submit_card(player_id, message)
            return
        if isinstance(message, SubmitRowChoice):
            self._handle_submit_row_choice(player_id, message)
            return
        raise TypeError(f"unsupported client message type: {type(message)!r}")

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

    def _handle_submit_card(self, player_id: PlayerID, message: SubmitCard) -> None:
        submit_play_card(self.state, player_id, message.card_value)
        if not all_cards_selected(self.state):
            return

        revealed_plays = begin_trick_resolution(self.state)
        self.outbox.append(self._build_cards_revealed(revealed_plays))
        self._advance_resolution_until_blocked()

    def _handle_submit_row_choice(self, player_id: PlayerID, message: SubmitRowChoice) -> None:
        submit_choose_row(self.state, player_id, message.row_id)
        self.outbox.append(RowChoiceCommitted(row_id=message.row_id))
        self._advance_resolution_until_blocked()

    def _advance_resolution_until_blocked(self) -> None:
        while True:
            if has_pending_row_choice(self.state):
                active_player_id = self.state.phase_info.active_player_id
                if active_player_id is None:
                    raise ValueError("missing active_player_id for choose-row phase")
                self.outbox.append(
                    ChooseRowRequested(
                        player_id=active_player_id,
                        state=self.build_player_state_for(active_player_id),
                    )
                )
                return

            if has_pending_resolution_step(self.state):
                step_or_prompt = resolve_next_trick_step(self.state)
                if isinstance(step_or_prompt, RowChoiceRequired | TrickResolutionStep):
                    continue

            if trick_resolution_finished(self.state):
                self._finish_current_trick()
                return

            return

    def _finish_current_trick(self) -> None:
        result = finish_trick(self.state)
        self.outbox.append(StateUpdated(state=self.build_public_state()))
        if not result.game_finished:
            self._request_choose_cards_for_current_trick()

    def _build_cards_revealed(self, plays: tuple[RevealedPlay, ...]) -> CardsRevealed:
        return CardsRevealed(
            played_cards=tuple(
                PlayedCardView(
                    player_id=play.player_id,
                    player_name=self.state.get_player_by_id(play.player_id).name,
                    card_value=play.card.value,
                )
                for play in plays
            )
        )
