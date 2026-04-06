from __future__ import annotations

import random
from dataclasses import dataclass, field

from row_taker.engine.phases import Phase
from row_taker.engine.player_state_ops import playable_cards, selectable_row_ids
from row_taker.hub.messages import ChooseCardRequested, ChooseRowRequested, ClientToHubMessage, HubToClientMessage, SubmitCard, SubmitRowChoice


@dataclass(slots=True)
class RandomBotClient:
    rng: random.Random = field(default_factory=random.Random)

    def handle_hub_message(self, message: HubToClientMessage) -> ClientToHubMessage | None:
        if isinstance(message, ChooseCardRequested):
            state = message.state
            state.validate_phase(Phase.CHOOSE_CARD)
            state.validate_hand_not_empty()

            card = self.rng.choice(playable_cards(state))
            return SubmitCard(
                player_id=state.self_player_id,
                card_value=card.value,
            )

        if isinstance(message, ChooseRowRequested):
            state = message.state
            state.validate_phase(Phase.CHOOSE_ROW)

            row_id = self.rng.choice(list(selectable_row_ids(state)))
            return SubmitRowChoice(
                player_id=state.self_player_id,
                row_id=row_id,
            )

        return None
