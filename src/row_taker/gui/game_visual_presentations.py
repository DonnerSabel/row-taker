from __future__ import annotations

from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationGameFinished,
    PresentationOverflowResolved,
    PresentationRoundFinished,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
    PresentationTrickFinished,
)
from row_taker.client.state import ClientState
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.state import PublicState
from row_taker.gui.game_visual_invariants import assert_visual_matches_public_state
from row_taker.gui.game_visual_state import (
    GameVisualState,
    GameVisualStep,
    PlayerPlayAnchor,
    RowCardAnchor,
    RowEmphasis,
    VisualCard,
    VisualCardMotion,
    VisualTransition,
)
from row_taker.gui.game_visual_static import build_stable_game_visual_state

CARD_PLACEMENT_DURATION_FRAMES = 32
ROW_REPLACEMENT_DURATION_FRAMES = 32


def build_row_choice_visual_state(
    state: ClientState,
) -> GameVisualState:
    presentation_step = state.current_presentation_step
    if presentation_step is None or not isinstance(
        presentation_step.event,
        PresentationRowChoiceRequired | PresentationRowChosen,
    ):
        raise ValueError(
            "current presentation step is neither "
            "PresentationRowChoiceRequired nor PresentationRowChosen"
        )

    event = presentation_step.event
    row_emphasis: dict[RowID, RowEmphasis] = {}
    if isinstance(event, PresentationRowChosen):
        row_emphasis[event.row_id] = "choice"

    selected_hand_card_value = event.card_value if event.player_id == state.own_player_id else None
    return build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_before,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        staged_card_values_override={event.player_id: event.card_value},
        selected_hand_card_value=selected_hand_card_value,
    )


def build_row_replacement_visual_step(
    state: ClientState,
) -> GameVisualStep:
    presentation_step = state.current_presentation_step
    if presentation_step is None or not isinstance(
        presentation_step.event,
        PresentationRowTaken | PresentationOverflowResolved,
    ):
        raise ValueError(
            "current presentation step is neither "
            "PresentationRowTaken nor PresentationOverflowResolved"
        )

    event = presentation_step.event
    if isinstance(event, PresentationRowTaken):
        replacement_card_value = event.replacement_card_value
        emphasis: RowEmphasis = "taken"
    else:
        replacement_card_value = event.card_value
        emphasis = "overflow"

    completed_cards = _completed_card_values_by_player(state)
    hidden_player_ids = frozenset((*completed_cards, event.player_id))
    hidden_hand_card_values = frozenset(
        card_value
        for player_id, card_value in (
            *completed_cards.items(),
            (event.player_id, replacement_card_value),
        )
        if player_id == state.own_player_id
    )
    row_emphasis = {event.row_id: emphasis}
    taken_cards = _visual_cards_for_row(
        presentation_step.public_state_before,
        event.row_id,
    )
    if tuple(card.card_value for card in taken_cards) != event.taken_cards:
        raise ValueError(
            "row replacement snapshot does not match the presented cards: "
            f"row={event.row_id!r}, cards={event.taken_cards!r}"
        )
    taken_cards_by_row_id = {event.row_id: taken_cards}

    after = build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_after,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        taken_cards_by_row_id=taken_cards_by_row_id,
    )
    visual_row_order = tuple(row.row_id for row in after.rows)
    before = build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_before,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        taken_cards_by_row_id=taken_cards_by_row_id,
        visual_row_order=visual_row_order,
    )

    assert_visual_matches_public_state(before, presentation_step.public_state_before)
    assert_visual_matches_public_state(after, presentation_step.public_state_after)

    target_row = after.row_by_id(event.row_id)
    if target_row is None or target_row.card_values != event.row_cards_after:
        raise ValueError(
            "row replacement after snapshot does not match the replacement row: "
            f"row={event.row_id!r}, cards={event.row_cards_after!r}"
        )
    if target_row.card_values != (replacement_card_value,):
        raise ValueError(
            "replacement row must contain only the replacement card: "
            f"row={event.row_id!r}, card={replacement_card_value}"
        )

    return GameVisualStep(
        before=before,
        after=after,
        transition=VisualTransition(
            card_motions=(
                VisualCardMotion(
                    card_value=replacement_card_value,
                    source=PlayerPlayAnchor(
                        player_id=event.player_id,
                        card_value=replacement_card_value,
                    ),
                    target=RowCardAnchor(
                        row_id=event.row_id,
                        card_index=0,
                    ),
                ),
            ),
            duration_frames=ROW_REPLACEMENT_DURATION_FRAMES,
        ),
    )


def build_finished_visual_state(
    state: ClientState,
) -> GameVisualState:
    presentation_step = state.current_presentation_step
    if presentation_step is None or not isinstance(
        presentation_step.event,
        PresentationTrickFinished | PresentationRoundFinished | PresentationGameFinished,
    ):
        raise ValueError("current presentation step is not a finish event")

    event = presentation_step.event
    if isinstance(event, PresentationRoundFinished):
        status_message = "Runde beendet"
    elif isinstance(event, PresentationGameFinished):
        status_message = "Spiel beendet"
    else:
        status_message = None

    completed_cards = _completed_card_values_by_player(state)
    hidden_player_ids = frozenset(completed_cards)
    hidden_hand_card_values = frozenset(
        card_value
        for player_id, card_value in completed_cards.items()
        if player_id == state.own_player_id
    )
    visual_state = build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_after,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        status_message=status_message,
        status_message_level="info",
    )
    assert_visual_matches_public_state(
        visual_state,
        presentation_step.public_state_after,
    )
    return visual_state


def _visual_cards_for_row(
    public_state: PublicState,
    row_id: RowID,
) -> tuple[VisualCard, ...]:
    row = public_state.rows[public_state.get_row_index(row_id)]
    return tuple(VisualCard(card_value=card.value, bullheads=card.bullheads) for card in row.cards)


def build_card_placed_visual_step(
    state: ClientState,
) -> GameVisualStep:
    presentation_step = state.current_presentation_step
    if presentation_step is None or not isinstance(
        presentation_step.event,
        PresentationCardPlaced,
    ):
        raise ValueError("current presentation step is not PresentationCardPlaced")

    event = presentation_step.event
    completed_cards = _completed_card_values_by_player(state)
    hidden_player_ids = frozenset((*completed_cards, event.player_id))
    hidden_hand_card_values = frozenset(
        card_value
        for player_id, card_value in (
            *completed_cards.items(),
            (event.player_id, event.card_value),
        )
        if player_id == state.own_player_id
    )
    row_emphasis = {event.row_id: "placed"}

    after = build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_after,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
    )
    visual_row_order = tuple(row.row_id for row in after.rows)
    before = build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_before,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        visual_row_order=visual_row_order,
    )

    assert_visual_matches_public_state(before, presentation_step.public_state_before)
    assert_visual_matches_public_state(after, presentation_step.public_state_after)

    target_row = after.row_by_id(event.row_id)
    if target_row is None or not target_row.cards:
        raise ValueError(f"card placement target row {event.row_id!r} is missing")
    if target_row.cards[-1].card_value != event.card_value:
        raise ValueError(
            "card placement snapshot does not end with the presented card: "
            f"row={event.row_id!r}, card={event.card_value}"
        )

    return GameVisualStep(
        before=before,
        after=after,
        transition=VisualTransition(
            card_motions=(
                VisualCardMotion(
                    card_value=event.card_value,
                    source=PlayerPlayAnchor(
                        player_id=event.player_id,
                        card_value=event.card_value,
                    ),
                    target=RowCardAnchor(
                        row_id=event.row_id,
                        card_index=len(target_row.cards) - 1,
                    ),
                ),
            ),
            duration_frames=CARD_PLACEMENT_DURATION_FRAMES,
        ),
    )


def _completed_card_values_by_player(state: ClientState) -> dict[PlayerID, int]:
    completed: dict[PlayerID, int] = {}
    for step in state.presentation_steps:
        event = step.event
        if isinstance(event, PresentationCardPlaced | PresentationOverflowResolved):
            completed[event.player_id] = event.card_value
        elif isinstance(event, PresentationRowTaken):
            completed[event.player_id] = event.replacement_card_value
    return completed
