from row_taker.engine.cards import Card
from row_taker.engine.lobby.config import MatchConfig, SeatConfig
from row_taker.engine.lobby.state import LobbyState
from row_taker.engine.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.phases import Phase, PhaseInfo
from row_taker.engine.state import DeltaPublicState, PlayerState, PublicState, RulesConfig
from row_taker.protocol.codec import (
    client_message_from_dict,
    client_message_to_dict,
    server_message_from_dict,
    server_message_to_dict,
)
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ConfigureLobby,
    GameStarting,
    LobbyStateUpdated,
    StartGame,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)


def _public_state() -> PublicState:
    return PublicState(
        config=RulesConfig(),
        players=[PublicPlayerInfo(player_id=PlayerID('player-0'), name='A', score=3, hand_count=7)],
        rows=[Row(row_id=RowID('row-0'), cards=[Card(10)])],
        round_no=2,
        trick_no=5,
        phase_info=PhaseInfo(phase=Phase.CHOOSE_CARD, message='Choose one card.'),
    )


def _match_config() -> MatchConfig:
    return MatchConfig.from_seats([
        SeatConfig.human(0, 'A'),
        SeatConfig.random_bot(1, 'Bot_1'),
    ])


def _lobby_state(*, game_started: bool = False) -> LobbyState:
    return LobbyState(match_config=_match_config(), game_started=game_started)


def test_client_protocol_codec_roundtrip() -> None:
    submit_card = SubmitCard(player_id=PlayerID('player-0'), card_value=42)
    assert client_message_from_dict(client_message_to_dict(submit_card)) == submit_card

    submit_row = SubmitRowChoice(player_id=PlayerID('player-0'), row_id=RowID('row-2'))
    assert client_message_from_dict(client_message_to_dict(submit_row)) == submit_row

    configure_lobby = ConfigureLobby(match_config=_match_config())
    assert client_message_from_dict(client_message_to_dict(configure_lobby)) == configure_lobby

    start_game = StartGame()
    assert client_message_from_dict(client_message_to_dict(start_game)) == start_game


def test_server_protocol_codec_roundtrip() -> None:
    public_state = _public_state()
    player_state = PlayerState(public_state=public_state, self_player_id=PlayerID('player-0'), hand=[Card(42)])
    delta = DeltaPublicState(
        player_id=PlayerID('player-0'),
        affected_row_id=RowID('row-0'),
        new_row_cards=(Card(10), Card(42)),
    )

    lobby_updated = LobbyStateUpdated(lobby_state=_lobby_state())
    assert server_message_from_dict(server_message_to_dict(lobby_updated)) == lobby_updated

    game_starting = GameStarting(lobby_state=_lobby_state(game_started=True))
    assert server_message_from_dict(server_message_to_dict(game_starting)) == game_starting

    state_updated = StateUpdated(state=public_state)
    assert server_message_from_dict(server_message_to_dict(state_updated)) == state_updated

    choose_card = ChooseCardRequested(player_id=PlayerID('player-0'), state=player_state)
    assert server_message_from_dict(server_message_to_dict(choose_card)) == choose_card

    trick_resolved = TrickResolved(deltas=(delta,), new_round_started=False, game_finished=False)
    assert server_message_from_dict(server_message_to_dict(trick_resolved)) == trick_resolved
