from __future__ import annotations

import random

import pytest

from row_taker.engine.game import setup_game
from row_taker.engine.game.models import PlayerID
from row_taker.protocol.messages import (
    ChooseCardRequested,
    SessionEnded,
    SessionEndReason,
    StateUpdated,
    SubmitCard,
)
from row_taker.server.errors import ClientRequestRejected
from row_taker.server.match_participants import MatchParticipants
from row_taker.server.match_session_router import MatchSessionRouter


def _participants() -> MatchParticipants:
    return MatchParticipants(
        ordered_client_ids=("client-0", "client-1"),
        player_to_client_id={
            PlayerID("player-0"): "client-0",
            PlayerID("player-1"): "client-1",
        },
        client_to_player_id={
            "client-0": PlayerID("player-0"),
            "client-1": PlayerID("player-1"),
        },
    )


def test_start_routes_revisioned_match_messages_to_clients() -> None:
    router = MatchSessionRouter()

    router.start(setup_game(["Alice", "Bob"], rng=random.Random(1234)), _participants())
    envelopes = router.drain_outgoing()

    assert isinstance(envelopes[0].message, StateUpdated)
    assert envelopes[0].message.revision == 1
    prompts = [
        envelope for envelope in envelopes if isinstance(envelope.message, ChooseCardRequested)
    ]
    assert [envelope.message.revision for envelope in prompts] == [2, 3]
    assert [envelope.target_client_id for envelope in prompts] == ["client-0", "client-1"]


def test_game_message_is_validated_and_forwarded_by_client_mapping() -> None:
    router = MatchSessionRouter()
    router.start(setup_game(["Alice", "Bob"], rng=random.Random(1234)), _participants())
    router.drain_outgoing()
    card_value = router.state.players[0].hand[0].value

    router.handle_client_message("client-0", SubmitCard(card_value=card_value))

    assert router.state.selected_cards[PlayerID("player-0")].value == card_value


def test_unknown_client_is_rejected_without_touching_match() -> None:
    router = MatchSessionRouter()
    router.start(setup_game(["Alice", "Bob"], rng=random.Random(1234)), _participants())
    router.drain_outgoing()

    with pytest.raises(ClientRequestRejected, match="not assigned"):
        router.handle_client_message("client-x", SubmitCard(card_value=1))

    assert router.state.selected_cards == {}


def test_abort_routes_session_end_and_clears_match_state() -> None:
    router = MatchSessionRouter()
    router.start(setup_game(["Alice", "Bob"], rng=random.Random(1234)), _participants())
    router.drain_outgoing()

    router.abort(
        departing_client_id="client-0",
        departing_display_name="Alice",
        reason=SessionEndReason.QUIT,
        message="Alice left",
        remaining_client_ids=("client-1",),
    )
    envelopes = router.drain_outgoing()

    assert len(envelopes) == 1
    assert envelopes[0].target_client_id == "client-1"
    assert isinstance(envelopes[0].message, SessionEnded)
    assert not router.is_active
    assert router.player_to_client_id == {}
    assert router.client_to_player_id == {}
