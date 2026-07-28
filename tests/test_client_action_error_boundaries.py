from __future__ import annotations

import pytest
from client_test_support import player_state_for

import row_taker.client.action_transitions as transitions
from row_taker.client.actions import ClientActionChooseCard
from row_taker.client.state import initial_client_state, request_card_choice


def test_submit_card_turns_expected_validation_error_into_local_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    player_state = player_state_for(0)
    state = request_card_choice(
        initial_client_state(),
        player_state.self_player_id,
        player_state,
    )

    def reject_card(player_state: object, card_value: int) -> None:
        del player_state, card_value
        raise ValueError("card rejected")

    monkeypatch.setattr(transitions, "validate_submit_card", reject_card)

    result = transitions.submit_card(state, ClientActionChooseCard(card_value=1))

    assert result.state is state
    assert result.local_message == "card rejected"
    assert result.outbound_message is None


def test_submit_card_does_not_hide_unexpected_programming_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    player_state = player_state_for(0)
    state = request_card_choice(
        initial_client_state(),
        player_state.self_player_id,
        player_state,
    )

    def fail_unexpectedly(player_state: object, card_value: int) -> None:
        del player_state, card_value
        raise RuntimeError("programming error")

    monkeypatch.setattr(transitions, "validate_submit_card", fail_unexpectedly)

    with pytest.raises(RuntimeError, match="programming error"):
        transitions.submit_card(state, ClientActionChooseCard(card_value=1))
