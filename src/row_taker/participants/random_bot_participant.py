from __future__ import annotations

import random
from dataclasses import dataclass, field

from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.phases import Phase
from row_taker.engine.state import PlayerState


@dataclass(slots=True)
class RandomBotParticipant:
    rng: random.Random = field(default_factory=random.Random)

    def on_choose_card_request(self, state: PlayerState) -> PlayCardCommand:
        state.validate_phase(Phase.CHOOSE_CARD)
        state.validate_hand_not_empty()

        card = self.rng.choice(state.hand)
        return PlayCardCommand(
            player_id=state.self_player_id,
            card_value=card.value,
        )

    def on_choose_row_request(self, state: PlayerState) -> ChooseRowCommand:
        state.validate_phase(Phase.CHOOSE_ROW)

        candidates = list(state.get_selectable_row_ids_for_choose_row())
        row_id = self.rng.choice(candidates)
        return ChooseRowCommand(
            player_id=state.self_player_id,
            row_id=row_id,
        )
