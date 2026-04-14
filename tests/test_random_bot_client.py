from __future__ import annotations

import random

from row_taker.bots.random_bot_client import RandomBotClient
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PlayerState, PublicState, RulesConfig
from row_taker.protocol.messages import ChooseCardRequested, ChooseRowRequested, SubmitCard, SubmitRowChoice


def _choose_card_state() -> PlayerState:
    return PlayerState(
        public_state=PublicState(
            config=RulesConfig(hand_size=2),
            players=[
                PublicPlayerInfo(player_id=PlayerID('player-0'), name='Bot', score=0, hand_count=2),
                PublicPlayerInfo(player_id=PlayerID('player-1'), name='Alice', score=0, hand_count=2),
            ],
            rows=[
                Row(row_id=RowID('row-0'), cards=[Card(10)]),
                Row(row_id=RowID('row-1'), cards=[Card(20)]),
                Row(row_id=RowID('row-2'), cards=[Card(30)]),
                Row(row_id=RowID('row-3'), cards=[Card(40)]),
            ],
            round_no=1,
            trick_no=1,
            phase_info=PhaseInfo(phase=Phase.CHOOSE_CARD, active_player_id=PlayerID('player-0'), selectable_row_ids=()),
        ),
        self_player_id=PlayerID('player-0'),
        hand=[Card(11), Card(17)],
    )


def _choose_row_state() -> PlayerState:
    return PlayerState(
        public_state=PublicState(
            config=RulesConfig(hand_size=2),
            players=[
                PublicPlayerInfo(player_id=PlayerID('player-0'), name='Bot', score=0, hand_count=1),
                PublicPlayerInfo(player_id=PlayerID('player-1'), name='Alice', score=0, hand_count=1),
            ],
            rows=[
                Row(row_id=RowID('row-0'), cards=[Card(10)]),
                Row(row_id=RowID('row-1'), cards=[Card(20)]),
                Row(row_id=RowID('row-2'), cards=[Card(30)]),
                Row(row_id=RowID('row-3'), cards=[Card(40)]),
            ],
            round_no=1,
            trick_no=1,
            phase_info=PhaseInfo(phase=Phase.CHOOSE_ROW, active_player_id=PlayerID('player-0'), selectable_row_ids=(RowID('row-1'), RowID('row-3'))),
        ),
        self_player_id=PlayerID('player-0'),
        hand=[Card(5)],
    )


def test_random_bot_client_uses_game_client_core_for_card_choice() -> None:
    bot = RandomBotClient(rng=random.Random(1234))
    responses = bot.handle_server_message(ChooseCardRequested(player_id=PlayerID('player-0'), state=_choose_card_state()))
    assert len(responses) == 1
    assert isinstance(responses[0], SubmitCard)
    assert responses[0].card_value in {11, 17}


def test_random_bot_client_uses_game_client_core_for_row_choice() -> None:
    bot = RandomBotClient(rng=random.Random(1234))
    responses = bot.handle_server_message(ChooseRowRequested(player_id=PlayerID('player-0'), state=_choose_row_state()))
    assert len(responses) == 1
    assert isinstance(responses[0], SubmitRowChoice)
    assert responses[0].row_id in {RowID('row-1'), RowID('row-3')}
