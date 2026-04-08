from row_taker.engine.cards import Card
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.models import PublicPlayerInfo, Row
from row_taker.engine.phases import Phase, PhaseInfo
from row_taker.engine.state import PlayerState, PublicState, RulesConfig
from row_taker.protocol.messages import ChooseCardRequested, ChooseRowRequested, SubmitCard, SubmitRowChoice
from row_taker.server.endpoints import LocalLoopbackEndpoint
from row_taker.server.process_bot_runner import ProcessBotRunner


def _player_state(phase: Phase) -> PlayerState:
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
            phase_info=PhaseInfo(
                phase=phase,
                active_player_id=PlayerID('player-0'),
                selectable_row_ids=(RowID('row-1'), RowID('row-3')) if phase == Phase.CHOOSE_ROW else (),
            ),
        ),
        self_player_id=PlayerID('player-0'),
        hand=[Card(11), Card(17)],
    )


def test_process_bot_runner_returns_json_framed_card_response() -> None:
    endpoint = LocalLoopbackEndpoint()
    runner = ProcessBotRunner(endpoint=endpoint, seed=1234)
    try:
        endpoint.deliver(ChooseCardRequested(player_id=PlayerID('player-0'), state=_player_state(Phase.CHOOSE_CARD)))
        handled = runner.pump()
        outgoing = endpoint.drain_outgoing()
    finally:
        runner.close()

    assert handled == 1
    assert len(outgoing) == 1
    assert isinstance(outgoing[0], SubmitCard)
    assert outgoing[0].player_id == PlayerID('player-0')
    assert outgoing[0].card_value in {11, 17}


def test_process_bot_runner_returns_json_framed_row_choice() -> None:
    endpoint = LocalLoopbackEndpoint()
    runner = ProcessBotRunner(endpoint=endpoint, seed=1234)
    try:
        endpoint.deliver(ChooseRowRequested(player_id=PlayerID('player-0'), state=_player_state(Phase.CHOOSE_ROW)))
        handled = runner.pump()
        outgoing = endpoint.drain_outgoing()
    finally:
        runner.close()

    assert handled == 1
    assert len(outgoing) == 1
    assert isinstance(outgoing[0], SubmitRowChoice)
    assert outgoing[0].player_id == PlayerID('player-0')
    assert outgoing[0].row_id in {RowID('row-1'), RowID('row-3')}
