from __future__ import annotations

import socket
import threading

from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.models import PublicPlayerInfo, Row
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PlayerState, PublicState, RulesConfig
from row_taker.protocol.messages import ChooseCardRequested, JoinLobby, SubmitCard
from row_taker.protocol.transport import ServerTransport
from row_taker.server.bot_process_handle import BotProcessHandle


def _player_state() -> PlayerState:
    return PlayerState(
        public_state=PublicState(
            config=RulesConfig(hand_size=2),
            players=[
                PublicPlayerInfo(player_id=PlayerID("player-0"), name="Bot", score=0, hand_count=2),
                PublicPlayerInfo(player_id=PlayerID("player-1"), name="Alice", score=0, hand_count=2),
            ],
            rows=[
                Row(row_id=RowID("row-0"), cards=[Card(10)]),
                Row(row_id=RowID("row-1"), cards=[Card(20)]),
                Row(row_id=RowID("row-2"), cards=[Card(30)]),
                Row(row_id=RowID("row-3"), cards=[Card(40)]),
            ],
            round_no=1,
            trick_no=1,
            phase_info=PhaseInfo(
                phase=Phase.CHOOSE_CARD,
                active_player_id=PlayerID("player-0"),
                selectable_row_ids=(),
            ),
        ),
        self_player_id=PlayerID("player-0"),
        hand=[Card(11), Card(17)],
    )


def test_bot_process_joins_and_responds_over_tcp() -> None:
    results: list[object] = []
    ready = threading.Event()

    def worker(listener: socket.socket) -> None:
        ready.set()
        conn, _ = listener.accept()
        transport = ServerTransport.from_socket(conn)
        try:
            join_message = transport.receive()
            results.append(join_message)
            transport.send(ChooseCardRequested(player_id=PlayerID("player-0"), state=_player_state()))
            response = transport.receive()
            results.append(response)
        finally:
            transport.close()
            listener.close()

    listener = socket.create_server(("127.0.0.1", 0), reuse_port=False)
    host, port = listener.getsockname()
    thread = threading.Thread(target=worker, args=(listener,), daemon=True)
    thread.start()
    ready.wait(timeout=2)

    handle = BotProcessHandle.spawn(
        host=host,
        port=port,
        display_name="Bot_Bob",
        client_id="bot-1",
        seed=1234,
    )
    thread.join(timeout=5)
    handle.close()

    assert results
    assert results[0] == JoinLobby(display_name="Bot_Bob", requested_client_id="bot-1")
    assert isinstance(results[1], SubmitCard)
    assert results[1].player_id == PlayerID("player-0")
