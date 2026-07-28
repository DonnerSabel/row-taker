from __future__ import annotations

from itertools import pairwise

from row_taker.client.core_reducer import reduce_server_message
from row_taker.client.core_state import ClientCoreState
from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationCardsRevealed,
    PresentationOverflowResolved,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
    PresentationTrickFinished,
)
from row_taker.client.presentation_queue import advance_presentation_queue
from row_taker.client.state import ClientState
from row_taker.client.trick_presentation_resolver import (
    apply_trick_row_choice,
    start_trick_presentation,
)
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PublicState, RulesConfig
from row_taker.protocol.messages import CardsRevealed, PlayedCardView


def _public_state() -> PublicState:
    return PublicState(
        config=RulesConfig(hand_size=2),
        players=tuple(
            PublicPlayerInfo(
                player_id=PlayerID(f"player-{index}"),
                name=name,
                score=0,
                hand_count=2,
            )
            for index, name in enumerate(("Ada", "Ben", "Clara", "Dorian"))
        ),
        rows=(
            Row(RowID("row-0"), tuple(Card(value) for value in (10, 20, 30, 40, 50))),
            Row(RowID("row-1"), (Card(65),)),
            Row(RowID("row-2"), (Card(78),)),
            Row(RowID("row-3"), (Card(92),)),
        ),
        round_no=1,
        trick_no=1,
        phase_info=PhaseInfo(phase=Phase.REVEAL_AND_RESOLVE),
    )


def _revealed() -> CardsRevealed:
    values = (7, 53, 66, 95)
    names = ("Ada", "Ben", "Clara", "Dorian")
    return CardsRevealed(
        plays=tuple(
            PlayedCardView(
                player_id=PlayerID(f"player-{index}"),
                player_name=name,
                card_value=value,
            )
            for index, (name, value) in enumerate(zip(names, values, strict=True))
        )
    )


def _row_values(state: PublicState, row_id: RowID) -> tuple[int, ...]:
    return tuple(card.value for card in state.rows[state.get_row_index(row_id)].cards)


def test_start_presentation_captures_unchanged_steps_until_row_choice() -> None:
    public_state = _public_state()

    presentation = start_trick_presentation(public_state, _revealed())

    assert presentation.pending_row_choice is not None
    assert tuple(type(step.event) for step in presentation.presentation_steps) == (
        PresentationCardsRevealed,
        PresentationRowChoiceRequired,
    )
    for step in presentation.presentation_steps:
        assert step.public_state_before == public_state
        assert step.public_state_after == public_state


def test_row_choice_resumes_with_chained_before_after_snapshots() -> None:
    initial = _public_state()
    blocked = start_trick_presentation(initial, _revealed())

    completed = apply_trick_row_choice(blocked, RowID("row-1"))

    assert tuple(type(step.event) for step in completed.presentation_steps) == (
        PresentationCardsRevealed,
        PresentationRowChoiceRequired,
        PresentationRowChosen,
        PresentationRowTaken,
        PresentationOverflowResolved,
        PresentationCardPlaced,
        PresentationCardPlaced,
        PresentationTrickFinished,
    )
    for previous, following in pairwise(completed.presentation_steps):
        assert previous.public_state_after == following.public_state_before

    row_taken = completed.presentation_steps[3]
    assert _row_values(row_taken.public_state_before, RowID("row-1")) == (65,)
    assert _row_values(row_taken.public_state_after, RowID("row-1")) == (7,)
    assert row_taken.public_state_after.players[0].score > row_taken.public_state_before.players[0].score

    overflow = completed.presentation_steps[4]
    assert _row_values(overflow.public_state_before, RowID("row-0")) == (10, 20, 30, 40, 50)
    assert _row_values(overflow.public_state_after, RowID("row-0")) == (53,)
    assert overflow.public_state_after.players[1].score > overflow.public_state_before.players[1].score

    assert completed.shadow_state == completed.presentation_steps[-1].public_state_after
    assert len(completed.resolution_steps) == 4


def test_client_queues_presentation_steps_directly() -> None:
    public_state = _public_state()
    state = reduce_server_message(
        ClientState(core_state=ClientCoreState(public_state=public_state)),
        _revealed(),
    )

    assert state.presentation_steps == ()
    assert state.pending_presentation_steps
    assert state.current_presentation_step == state.pending_presentation_steps[0]

    advanced = advance_presentation_queue(state)

    assert advanced.presentation_steps == (state.pending_presentation_steps[0],)
    assert advanced.pending_presentation_steps == state.pending_presentation_steps[1:]
