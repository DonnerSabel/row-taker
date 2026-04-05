from __future__ import annotations

import random
from dataclasses import dataclass, field

from row_taker.engine.phases import Phase
from row_taker.hub.messages import ChooseCardRequested, ChooseRowRequested, SubmitCard, SubmitRowChoice
from row_taker.participants.client import ClientMessage, HubMessage


@dataclass(slots=True)
class RandomBotParticipant:
    rng: random.Random = field(default_factory=random.Random)

    def handle_hub_message(self, message: HubMessage) -> list[ClientMessage]:
        if isinstance(message, ChooseCardRequested):
            return [self._handle_choose_card_request(message)]

        if isinstance(message, ChooseRowRequested):
            return [self._handle_choose_row_request(message)]

        return []

    def _handle_choose_card_request(self, message: ChooseCardRequested) -> SubmitCard:
        state = message.state
        state.validate_phase(Phase.CHOOSE_CARD)
        state.validate_hand_not_empty()

        card = self.rng.choice(state.hand)
        return SubmitCard(
            player_id=state.self_player_id,
            card_value=card.value,
        )

    def _handle_choose_row_request(self, message: ChooseRowRequested) -> SubmitRowChoice:
        state = message.state
        state.validate_phase(Phase.CHOOSE_ROW)

        candidates = list(state.get_selectable_row_ids_for_choose_row())
        row_id = self.rng.choice(candidates)
        return SubmitRowChoice(
            player_id=state.self_player_id,
            row_id=row_id,
        )
