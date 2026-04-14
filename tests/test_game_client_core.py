from __future__ import annotations

from row_taker.client.core_state import ClientCoreState, ClientMode, PendingAction
from row_taker.client.presentation_events import PresentationCardsRevealed, PresentationRowTaken
from row_taker.client.state import ClientState
from row_taker.protocol.messages import CardsRevealed, PlayedCardView, RowChoiceCommitted, SessionEndReason, SessionEnded, StateUpdated

from client_test_support import apply_server_message, player_state_for


def test_state_updated_sets_public_state() -> None:
    player_state = player_state_for(0)
    state = ClientState()

    new_state = apply_server_message(state, StateUpdated(state=player_state.public_state))
    assert new_state.public_state == player_state.public_state


def test_choose_card_requested_enters_choose_card_state() -> None:
    player_state = player_state_for(0)
    state = ClientState()

    from row_taker.protocol.messages import ChooseCardRequested

    new_state = apply_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert new_state.own_player_id == player_state.self_player_id
    assert new_state.client_mode == ClientMode.GAME
    assert new_state.pending_action == PendingAction.CHOOSE_CARD


def test_cards_revealed_is_stored_in_core_state() -> None:
    player_state = player_state_for(0)
    revealed = CardsRevealed(
        plays=(
            PlayedCardView(
                player_id=player_state.self_player_id,
                player_name=player_state.self_player_name(),
                card_value=player_state.hand[0].value,
            ),
        ),
    )

    state = apply_server_message(ClientState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.public_state == player_state.public_state
    assert state.revealed_trick == revealed


def test_session_ended_exits_immediately() -> None:
    state = apply_server_message(
        ClientState(),
        SessionEnded(message="Spiel abgebrochen", reason=SessionEndReason.QUIT, client_id="client-0", display_name="Alice"),
    )

    assert state.should_exit is True
    assert state.session_error == "Spiel abgebrochen"


def test_cards_revealed_builds_trick_presentation_events() -> None:
    player_state = player_state_for(0)
    revealed = CardsRevealed(
        plays=(
            PlayedCardView(
                player_id=player_state.public_state.players[0].player_id,
                player_name=player_state.public_state.players[0].name,
                card_value=104,
            ),
            PlayedCardView(
                player_id=player_state.public_state.players[1].player_id,
                player_name=player_state.public_state.players[1].name,
                card_value=103,
            ),
        ),
    )

    state = apply_server_message(ClientState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.trick_presentation_state is not None
    assert state.pending_presentation_events
    assert isinstance(state.pending_presentation_events[0], PresentationCardsRevealed)


def test_row_choice_committed_advances_trick_presentation_state() -> None:
    player_state = player_state_for(0)
    lowest = min(row.cards[-1].value for row in player_state.public_state.rows)
    revealed = CardsRevealed(
        plays=(
            PlayedCardView(
                player_id=player_state.self_player_id,
                player_name=player_state.self_player_name(),
                card_value=lowest - 1,
            ),
        ),
    )

    state = apply_server_message(ClientState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)
    assert state.trick_presentation_state is not None
    assert state.trick_presentation_state.pending_row_choice is not None

    row_id = player_state.public_state.rows[0].row_id
    state = apply_server_message(state, RowChoiceCommitted(row_id=row_id))

    assert state.trick_presentation_state is not None
    assert state.trick_presentation_state.pending_row_choice is None
    assert any(isinstance(event, PresentationRowTaken) for event in state.pending_presentation_events)


def test_cards_revealed_queues_presentation_events_before_display() -> None:
    player_state = player_state_for(0)
    revealed = CardsRevealed(
        plays=(
            PlayedCardView(
                player_id=player_state.public_state.players[0].player_id,
                player_name=player_state.public_state.players[0].name,
                card_value=104,
            ),
        ),
    )

    state = apply_server_message(ClientState(core_state=ClientCoreState(public_state=player_state.public_state)), revealed)

    assert state.presentation_events == ()
    assert state.pending_presentation_events


def test_choose_card_requested_clears_visible_and_pending_presentation() -> None:
    player_state = player_state_for(0)
    state = ClientState(
        core_state=ClientCoreState(
            public_state=player_state.public_state,
            presentation_events=(PresentationCardsRevealed(plays=()),),
            pending_presentation_events=(PresentationCardsRevealed(plays=()),),
        ),
    )

    from row_taker.protocol.messages import ChooseCardRequested

    new_state = apply_server_message(
        state,
        ChooseCardRequested(player_id=player_state.self_player_id, state=player_state),
    )

    assert new_state.presentation_events == ()
    assert new_state.pending_presentation_events == ()
