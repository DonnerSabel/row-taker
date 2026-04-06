from __future__ import annotations

import random
from dataclasses import dataclass, field

from row_taker.engine.phases import Phase
from row_taker.hub.messages import ChooseCardRequested, ChooseRowRequested, SubmitCard, SubmitRowChoice, HubToClientMessage, ClientToHubMessage


@dataclass(slots=True)
class RandomBotClient:
    rng: random.Random = field(default_factory=random.Random)

    def handle_hub_message(self, message: HubToClientMessage) -> ClientToHubMessage | None:
        if isinstance(message, ChooseCardRequested):
            state = message.state
            state.validate_phase(Phase.CHOOSE_CARD)
            state.validate_hand_not_empty()

            card = self.rng.choice(state.hand)
            return SubmitCard(
                player_id=state.self_player_id,
                card_value=card.value,
            )

        if isinstance(message, ChooseRowRequested):
            state = message.state
            state.validate_phase(Phase.CHOOSE_ROW)

            candidates = list(state.get_selectable_row_ids_for_choose_row())
            row_id = self.rng.choice(candidates)
            return SubmitRowChoice(
                player_id=state.self_player_id,
                row_id=row_id,
            )

        return None
