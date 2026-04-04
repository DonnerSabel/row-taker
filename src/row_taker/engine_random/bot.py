from __future__ import annotations

import random

from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.state import PlayerState
from row_taker.participants.random_bot_participant import RandomBotParticipant


RandomBot = RandomBotParticipant


def choose_card_random(
    state: PlayerState,
    rng: random.Random | None = None,
) -> PlayCardCommand:
    bot = RandomBotParticipant(rng=random.Random() if rng is None else rng)
    return bot.on_choose_card_request(state)


def choose_row_random(
    state: PlayerState,
    rng: random.Random | None = None,
) -> ChooseRowCommand:
    bot = RandomBotParticipant(rng=random.Random() if rng is None else rng)
    return bot.on_choose_row_request(state)
