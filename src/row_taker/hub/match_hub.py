from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from row_taker.engine.cards import Card
from row_taker.engine.game import StepResult, start_next_round_if_needed
from row_taker.engine.models import PlayerID, RowID
from row_taker.engine.phases import Phase, PhaseInfo, StepAction
from row_taker.engine.rules import place_card, take_row, target_row_index
from row_taker.engine.state import GameState, PlayerState, PublicState
from row_taker.engine.views import build_player_state, build_public_state
from row_taker.hub.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


class WaitingState(StrEnum):
    IDLE = 'idle'
    WAITING_FOR_CARDS = 'waiting_for_cards'
    RESOLVING = 'resolving'
    WAITING_FOR_ROW_CHOICE = 'waiting_for_row_choice'
    TRICK_FINISHED = 'trick_finished'
    GAME_FINISHED = 'game_finished'


@dataclass(slots=True)
class MatchHub:
    state: GameState
    outbox: list[StateUpdated | ChooseCardRequested | ChooseRowRequested | TrickResolved] = field(
        default_factory=list
    )
    waiting_state: WaitingState = WaitingState.IDLE
    submitted_cards: dict[PlayerID, Card] = field(default_factory=dict)
    pending_resolution: list[tuple[PlayerID, Card]] = field(default_factory=list)
    resolution_results: list[StepResult] = field(default_factory=list)
    public_state_before_trick: PublicState | None = None
    pending_row_choice_player_id: PlayerID | None = None
    pending_row_choice_card: Card | None = None

    def start_trick(self) -> None:
        if self.is_finished():
            raise ValueError('cannot start trick: game is already finished')
        if self.waiting_state not in {WaitingState.IDLE, WaitingState.TRICK_FINISHED}:
            raise ValueError(f'cannot start trick while hub is in state {self.waiting_state!r}')
        if self.state.phase_info.phase != Phase.CHOOSE_CARD:
            raise ValueError(
                f'cannot start trick in phase {self.state.phase_info.phase!r}; expected {Phase.CHOOSE_CARD!r}'
            )

        self.submitted_cards.clear()
        self.pending_resolution.clear()
        self.resolution_results.clear()
        self.public_state_before_trick = self.build_public_state()
        self.pending_row_choice_player_id = None
        self.pending_row_choice_card = None
        self.waiting_state = WaitingState.WAITING_FOR_CARDS

        self._emit(StateUpdated(state=self.public_state_before_trick))
        for player in self.state.players:
            self._emit(
                ChooseCardRequested(
                    player_id=player.player_id,
                    state=self.build_player_state_for(player.player_id),
                )
            )

    def handle_client_message(self, message: SubmitCard | SubmitRowChoice) -> None:
        if isinstance(message, SubmitCard):
            self._handle_submit_card(message)
            return

        if isinstance(message, SubmitRowChoice):
            self._handle_submit_row_choice(message)
            return

        raise TypeError(f'unsupported client message: {type(message)!r}')

    def drain_outbox(self) -> list[StateUpdated | ChooseCardRequested | ChooseRowRequested | TrickResolved]:
        messages = list(self.outbox)
        self.outbox.clear()
        return messages

    def is_finished(self) -> bool:
        return self.state.phase_info.phase == Phase.GAME_OVER

    def build_public_state(self) -> PublicState:
        return build_public_state(self.state)

    def build_player_state_for(self, player_id: PlayerID) -> PlayerState:
        return build_player_state(self.state, player_id)

    def _handle_submit_card(self, message: SubmitCard) -> None:
        if self.waiting_state != WaitingState.WAITING_FOR_CARDS:
            raise ValueError(f'cannot submit card while hub is in state {self.waiting_state!r}')

        player_state = self.build_player_state_for(message.player_id)
        player_state.validate_phase(Phase.CHOOSE_CARD)

        if message.player_id in self.submitted_cards:
            raise ValueError(f'player {message.player_id!r} already submitted a card for this trick')

        card = Card(message.card_value)
        player_state.validate_has_card(card)
        self.submitted_cards[message.player_id] = card

        if len(self.submitted_cards) != len(self.state.players):
            return

        self._begin_resolution()
        self._resolve_until_blocked()

    def _handle_submit_row_choice(self, message: SubmitRowChoice) -> None:
        if self.waiting_state != WaitingState.WAITING_FOR_ROW_CHOICE:
            raise ValueError(f'cannot submit row choice while hub is in state {self.waiting_state!r}')
        if message.player_id != self.pending_row_choice_player_id:
            raise ValueError(
                f'row choice expected from {self.pending_row_choice_player_id!r}, got {message.player_id!r}'
            )
        if self.pending_row_choice_card is None:
            raise ValueError('missing pending row choice card')

        player_state = self.build_player_state_for(message.player_id)
        player_state.validate_phase(Phase.CHOOSE_ROW)
        player_state.validate_selectable_row_id(message.row_id)

        chosen_index = self.state.get_row_index(message.row_id)
        bullheads, _taken = take_row(self.state.rows, chosen_index)
        self.state.get_player_by_id(message.player_id).score += bullheads
        self.state.rows[chosen_index].cards = [self.pending_row_choice_card]

        self.resolution_results.append(
            StepResult(
                player_id=message.player_id,
                card=self.pending_row_choice_card,
                action=StepAction.TOOK_ROW_SMALL,
                row_id=message.row_id,
                bullheads_gained=bullheads,
            )
        )

        self.pending_row_choice_player_id = None
        self.pending_row_choice_card = None
        self.state.phase_info = PhaseInfo(
            phase=Phase.REVEAL_AND_RESOLVE,
            message='Revealing cards and resolving trick.',
        )
        self.waiting_state = WaitingState.RESOLVING
        self._resolve_until_blocked()

    def _begin_resolution(self) -> None:
        self.state.phase_info = PhaseInfo(
            phase=Phase.REVEAL_AND_RESOLVE,
            message='Revealing cards and resolving trick.',
        )
        self.state.validate_complete_play_selections(self.submitted_cards)

        for player_id, card in self.submitted_cards.items():
            self.state.validate_player_has_card(player_id, card)

        for player_id, card in self.submitted_cards.items():
            player = self.state.get_player_by_id(player_id)
            hand_index = next(
                index for index, hand_card in enumerate(player.hand)
                if hand_card.value == card.value
            )
            player.hand.pop(hand_index)

        self.state.selected_cards = dict(self.submitted_cards)
        ordered = sorted(self.submitted_cards.items(), key=lambda item: item[1].value)
        self.state.resolve_order = [player_id for player_id, _card in ordered]
        self.pending_resolution = list(ordered)
        self.waiting_state = WaitingState.RESOLVING

    def _resolve_until_blocked(self) -> None:
        while self.pending_resolution:
            player_id, card = self.pending_resolution.pop(0)
            row_index = target_row_index(self.state.rows, card)

            if row_index is None:
                selectable_row_ids = tuple(row.row_id for row in self.state.rows)
                self.state.phase_info = PhaseInfo(
                    phase=Phase.CHOOSE_ROW,
                    active_player_id=player_id,
                    pending_card=card,
                    selectable_row_ids=selectable_row_ids,
                    message='Choose a row to take.',
                )
                self.pending_row_choice_player_id = player_id
                self.pending_row_choice_card = card
                self.waiting_state = WaitingState.WAITING_FOR_ROW_CHOICE
                self._emit(
                    ChooseRowRequested(
                        player_id=player_id,
                        state=self.build_player_state_for(player_id),
                    )
                )
                return

            target_row = self.state.rows[row_index]
            bullheads, taken = place_card(
                self.state.rows,
                row_index,
                card,
                row_capacity=self.state.config.row_capacity,
            )

            action = StepAction.TOOK_ROW_OVERFLOW if taken is not None else StepAction.PLACED
            if taken is not None:
                self.state.get_player_by_id(player_id).score += bullheads

            self.resolution_results.append(
                StepResult(
                    player_id=player_id,
                    card=card,
                    action=action,
                    row_id=target_row.row_id,
                    bullheads_gained=bullheads,
                )
            )

        self._finish_trick()

    def _finish_trick(self) -> None:
        self.state.phase_info = PhaseInfo(
            phase=Phase.ROUND_SCORING,
            message='Trick finished.',
        )
        self.state.selected_cards.clear()
        self.state.resolve_order.clear()

        new_round_started = start_next_round_if_needed(self.state)
        game_finished = self.is_finished()
        self.waiting_state = WaitingState.GAME_FINISHED if game_finished else WaitingState.TRICK_FINISHED

        if self.public_state_before_trick is None:
            raise ValueError('missing public_state_before_trick while finishing trick')

        self._emit(
            TrickResolved(
                public_state_before=self.public_state_before_trick,
                resolution=list(self.resolution_results),
                public_state_after=self.build_public_state(),
                new_round_started=new_round_started,
                game_finished=game_finished,
            )
        )

    def _emit(self, message: StateUpdated | ChooseCardRequested | ChooseRowRequested | TrickResolved) -> None:
        self.outbox.append(message)
