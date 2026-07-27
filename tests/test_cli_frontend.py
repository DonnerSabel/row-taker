from __future__ import annotations

from client_test_support import apply_user_input, player_state_for

from row_taker.client.core_state import ClientCoreState, PendingAction
from row_taker.client.presentation_events import PresentationCardsRevealed, PresentationRowTaken
from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.state import ClientState, enter_game_mode
from row_taker.protocol.messages import LeaveSession


def _step(event) -> PresentationStep:
    public_state = player_state_for(0).public_state
    return PresentationStep(
        event=event,
        public_state_before=public_state,
        public_state_after=public_state,
    )


def test_uppercase_x_triggers_leave_session_and_suppresses_final_result() -> None:
    state, outbound = apply_user_input(ClientState(), "X")

    assert outbound == LeaveSession()
    assert state.should_exit is True
    assert state.suppress_final_result is True


def test_pending_presentation_enter_advances_queue() -> None:
    state = ClientState(
        core_state=ClientCoreState(
            pending_presentation_steps=(
                _step(PresentationCardsRevealed(plays=())),
                _step(PresentationRowTaken("p1", "Alice", 1, (1, 2), 3, 5, (5,))),
            ),
        ),
    )
    state = enter_game_mode(state, pending_action=PendingAction.NONE, player_state=None)

    state, _ = apply_user_input(state, "")

    assert len(state.presentation_steps) == 1
    assert len(state.pending_presentation_steps) == 1


def test_non_enter_during_pending_presentation_shows_hint() -> None:
    state = ClientState(
        core_state=ClientCoreState(
            pending_presentation_steps=(_step(PresentationCardsRevealed(plays=())),)
        ),
    )
    state = enter_game_mode(state, pending_action=PendingAction.NONE, player_state=None)

    state, _ = apply_user_input(state, "foo")

    assert state.flash_message is not None
    assert "Enter" in state.flash_message.text
