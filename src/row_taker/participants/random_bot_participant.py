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
        if state.phase_info.phase != Phase.CHOOSE_CARD:
            raise ValueError(
                f'on_choose_card_request called outside choose_card phase: {state.phase_info.phase!r}'
            )
        if not state.hand:
            raise ValueError('player hand is empty')

        card = self.rng.choice(state.hand)
        return PlayCardCommand(
            player_id=state.self_player_id,
            card_value=card.value,
        )

    def on_choose_row_request(self, state: PlayerState) -> ChooseRowCommand:
        if state.phase_info.phase != Phase.CHOOSE_ROW:
            raise ValueError(
                f'on_choose_row_request called outside choose_row phase: {state.phase_info.phase!r}'
            )

        candidates = list(state.phase_info.selectable_row_ids)
        if not candidates:
            candidates = [row.row_id for row in state.rows]

        if not candidates:
            raise ValueError('no rows available for choose_row')

        row_id = self.rng.choice(candidates)
        return ChooseRowCommand(
            player_id=state.self_player_id,
            row_id=row_id,
        )
