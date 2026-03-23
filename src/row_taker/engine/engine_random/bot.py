from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..commands import ChooseRowCommand, PlayCardCommand
from ..phases import Phase
from ..state import PlayerState


@dataclass(slots=True)
class RandomBot:
    rng: random.Random = field(default_factory=random.Random)

    def choose_card(self, state: PlayerState) -> PlayCardCommand:
        if state.phase_info.phase != Phase.CHOOSE_CARD:
            raise ValueError(
                f"RandomBot.choose_card called outside choose_card phase: {state.phase_info.phase!r}"
            )
        if not state.hand:
            raise ValueError("player hand is empty")

        card = self.rng.choice(state.hand)
        return PlayCardCommand(
            player_id=state.self_player_id,
            card_value=card.value,
        )

    def choose_row(self, state: PlayerState) -> ChooseRowCommand:
        if state.phase_info.phase != Phase.CHOOSE_ROW:
            raise ValueError(
                f"RandomBot.choose_row called outside choose_row phase: {state.phase_info.phase!r}"
            )

        candidates = list(state.phase_info.selectable_row_ids)
        if not candidates:
            candidates = [row.row_id for row in state.rows]

        if not candidates:
            raise ValueError("no rows available for choose_row")

        row_id = self.rng.choice(candidates)
        return ChooseRowCommand(
            player_id=state.self_player_id,
            row_id=row_id,
        )


def choose_card_random(
    state: PlayerState,
    rng: random.Random | None = None,
) -> PlayCardCommand:
    bot = RandomBot(rng=random.Random() if rng is None else rng)
    return bot.choose_card(state)


def choose_row_random(
    state: PlayerState,
    rng: random.Random | None = None,
) -> ChooseRowCommand:
    bot = RandomBot(rng=random.Random() if rng is None else rng)
    return bot.choose_row(state)
