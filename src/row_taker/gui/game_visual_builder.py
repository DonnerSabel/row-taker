from __future__ import annotations

from collections.abc import Mapping

from row_taker.client.core_state import PendingAction
from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationCardsRevealed,
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
from row_taker.gui.game_visual_invariants import (
    assert_selectable_objects_are_visible,
    assert_visual_matches_public_state,
)
from row_taker.gui.game_visual_state import (
    GameVisualState,
    GameVisualStep,
    PlayerPlayAnchor,
    RowCardAnchor,
    RowEmphasis,
    VisualCard,
    VisualCardMotion,
    VisualHandCard,
    VisualInteraction,
    VisualPlayer,
    VisualPresentationPanel,
    VisualRow,
    VisualStatus,
    VisualTransition,
)
from row_taker.gui.game_visual_transition import resolve_visual_step
from row_taker.client.presentation_text import format_presentation_event

CARD_PLACEMENT_DURATION_FRAMES = 32
ROW_REPLACEMENT_DURATION_FRAMES = 32


def build_game_visual_state(
    state: ClientState,
    *,
    last_action_summary: str,
    presentation_frame_count: int = 0,
    public_state_override: PublicState | None = None,
) -> GameVisualState:
    """Translate client semantics into the complete game-screen model."""

    if public_state_override is None:
        current_step = state.current_presentation_step
        if current_step is not None and isinstance(
            current_step.event,
            PresentationCardPlaced,
        ):
            visual_step = _build_card_placed_visual_step(
                state,
                last_action_summary=last_action_summary,
            )
            return resolve_visual_step(
                visual_step,
                presentation_frame_count=presentation_frame_count,
            )
        if current_step is not None and isinstance(
            current_step.event,
            PresentationRowTaken | PresentationOverflowResolved,
        ):
            visual_step = _build_row_replacement_visual_step(
                state,
                last_action_summary=last_action_summary,
            )
            return resolve_visual_step(
                visual_step,
                presentation_frame_count=presentation_frame_count,
            )
        if current_step is not None and isinstance(
            current_step.event,
            PresentationRowChoiceRequired | PresentationRowChosen,
        ):
            return _build_row_choice_visual_state(
                state,
                last_action_summary=last_action_summary,
            )
        if current_step is not None and isinstance(
            current_step.event,
            PresentationTrickFinished
            | PresentationRoundFinished
            | PresentationGameFinished,
        ):
            return _build_finished_visual_state(
                state,
                last_action_summary=last_action_summary,
            )

    return _build_stable_game_visual_state(
        state,
        public_state=public_state_override or state.public_state,
        last_action_summary=last_action_summary,
        presentation_panel=_build_cards_revealed_panel(state),
    )


def _build_row_choice_visual_state(
    state: ClientState,
    *,
    last_action_summary: str,
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
        headline = f"{event.player_name} wählt Reihe {event.row_id}"
    else:
        headline = f"{event.player_name} muss eine Reihe wählen"

    selected_hand_card_value = (
        event.card_value if event.player_id == state.own_player_id else None
    )
    return _build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_before,
        last_action_summary=last_action_summary,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        staged_card_values_override={event.player_id: event.card_value},
        selected_hand_card_value=selected_hand_card_value,
        presentation_panel=VisualPresentationPanel(
            headline=headline,
            details=_presentation_details(state),
            card_values=(event.card_value,),
        ),
    )


def _build_row_replacement_visual_step(
    state: ClientState,
    *,
    last_action_summary: str,
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
        headline = f"{event.player_name} nimmt Reihe {event.row_id}"
    else:
        replacement_card_value = event.card_value
        emphasis = "overflow"
        headline = f"Overflow: {event.player_name} nimmt Reihe {event.row_id}"

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
    panel = VisualPresentationPanel(
        headline=headline,
        details=_presentation_details(state),
        card_values=(replacement_card_value,),
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

    after = _build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_after,
        last_action_summary=last_action_summary,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        taken_cards_by_row_id=taken_cards_by_row_id,
        presentation_panel=panel,
    )
    visual_row_order = tuple(row.row_id for row in after.rows)
    before = _build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_before,
        last_action_summary=last_action_summary,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        taken_cards_by_row_id=taken_cards_by_row_id,
        visual_row_order=visual_row_order,
        presentation_panel=panel,
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


def _build_finished_visual_state(
    state: ClientState,
    *,
    last_action_summary: str,
) -> GameVisualState:
    presentation_step = state.current_presentation_step
    if presentation_step is None or not isinstance(
        presentation_step.event,
        PresentationTrickFinished
        | PresentationRoundFinished
        | PresentationGameFinished,
    ):
        raise ValueError("current presentation step is not a finish event")

    event = presentation_step.event
    if isinstance(event, PresentationTrickFinished):
        headline = "Stich beendet"
    elif isinstance(event, PresentationRoundFinished):
        headline = "Runde beendet"
    else:
        headline = "Spiel beendet"

    completed_cards = _completed_card_values_by_player(state)
    hidden_player_ids = frozenset(completed_cards)
    hidden_hand_card_values = frozenset(
        card_value
        for player_id, card_value in completed_cards.items()
        if player_id == state.own_player_id
    )
    visual_state = _build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_after,
        last_action_summary=last_action_summary,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        presentation_panel=VisualPresentationPanel(
            headline=headline,
            details=_presentation_details(state),
        ),
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
    return tuple(
        VisualCard(card_value=card.value, bullheads=card.bullheads)
        for card in row.cards
    )


def _build_card_placed_visual_step(
    state: ClientState,
    *,
    last_action_summary: str,
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
    panel = VisualPresentationPanel(
        headline=f"{event.player_name} legt {event.card_value}",
        details=_presentation_details(state),
        card_values=(event.card_value,),
    )
    row_emphasis = {event.row_id: "placed"}

    after = _build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_after,
        last_action_summary=last_action_summary,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        presentation_panel=panel,
    )
    visual_row_order = tuple(row.row_id for row in after.rows)
    before = _build_stable_game_visual_state(
        state,
        public_state=presentation_step.public_state_before,
        last_action_summary=last_action_summary,
        hidden_staged_player_ids=hidden_player_ids,
        hidden_hand_card_values=hidden_hand_card_values,
        active_player_id=event.player_id,
        row_emphasis_by_id=row_emphasis,
        visual_row_order=visual_row_order,
        presentation_panel=panel,
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


def _build_stable_game_visual_state(
    state: ClientState,
    *,
    public_state: PublicState | None,
    last_action_summary: str,
    hidden_staged_player_ids: frozenset[PlayerID] = frozenset(),
    hidden_hand_card_values: frozenset[int] = frozenset(),
    active_player_id: PlayerID | None = None,
    staged_card_values_override: Mapping[PlayerID, int] | None = None,
    selected_hand_card_value: int | None = None,
    row_emphasis_by_id: Mapping[RowID, RowEmphasis] | None = None,
    taken_cards_by_row_id: Mapping[RowID, tuple[VisualCard, ...]] | None = None,
    visual_row_order: tuple[RowID, ...] | None = None,
    presentation_panel: VisualPresentationPanel | None = None,
) -> GameVisualState:
    revealed_values = _revealed_card_values_by_player(state)
    if staged_card_values_override is not None:
        revealed_values = {**revealed_values, **staged_card_values_override}
    staged_values = {
        player_id: card_value
        for player_id, card_value in revealed_values.items()
        if player_id not in hidden_staged_player_ids
    }
    rows = _build_rows(
        public_state,
        emphasis_by_id=row_emphasis_by_id or {},
        taken_cards_by_id=taken_cards_by_row_id or {},
        visual_row_order=visual_row_order,
    )
    players = _build_players(
        state,
        public_state,
        revealed_values=staged_values,
        active_player_id=active_player_id,
    )
    hand = _build_hand(
        state,
        selected_card_value=(
            selected_hand_card_value
            if selected_hand_card_value is not None
            else _own_revealed_card_value(state, revealed_values)
        ),
        hidden_card_values=hidden_hand_card_values,
    )
    interaction = _build_interaction(state, hand)
    status = _build_status(
        state,
        public_state=public_state,
        players=players,
        last_action_summary=last_action_summary,
    )
    visual_state = GameVisualState(
        rows=rows,
        players=players,
        hand=hand,
        interaction=interaction,
        status=status,
        presentation_panel=presentation_panel,
    )
    assert_selectable_objects_are_visible(visual_state)
    return visual_state


def _build_rows(
    public_state: PublicState | None,
    *,
    emphasis_by_id: Mapping[RowID, RowEmphasis],
    taken_cards_by_id: Mapping[RowID, tuple[VisualCard, ...]],
    visual_row_order: tuple[RowID, ...] | None,
) -> tuple[VisualRow, ...]:
    if public_state is None:
        return ()

    rows = tuple(
        VisualRow(
            row_id=row.row_id,
            cards=tuple(
                VisualCard(card_value=card.value, bullheads=card.bullheads)
                for card in row.cards
            ),
            emphasis=emphasis_by_id.get(row.row_id, "none"),
            taken_cards=taken_cards_by_id.get(row.row_id, ()),
        )
        for row in public_state.rows
    )
    sorted_rows = tuple(sorted(rows, key=_visual_row_sort_key))
    if visual_row_order is None:
        return sorted_rows

    rows_by_id = {row.row_id: row for row in sorted_rows}
    if set(rows_by_id) != set(visual_row_order):
        raise ValueError("visual row order does not match public-state row ids")
    return tuple(rows_by_id[row_id] for row_id in visual_row_order)


def _visual_row_sort_key(row: VisualRow) -> tuple[int, str]:
    last_value = row.cards[-1].card_value if row.cards else -1
    return (last_value, str(row.row_id))


def _build_players(
    state: ClientState,
    public_state: PublicState | None,
    *,
    revealed_values: dict[PlayerID, int],
    active_player_id: PlayerID | None,
) -> tuple[VisualPlayer, ...]:
    if public_state is None:
        return ()

    return tuple(
        VisualPlayer(
            player_id=player.player_id,
            name=player.name,
            score=player.score,
            hand_count=player.hand_count,
            is_self=player.player_id == state.own_player_id,
            staged_card_value=revealed_values.get(player.player_id),
            emphasis="active" if player.player_id == active_player_id else "none",
        )
        for player in public_state.players
    )


def _revealed_card_values_by_player(state: ClientState) -> dict[PlayerID, int]:
    event = _current_cards_revealed_event(state)
    if event is not None:
        return {play.player_id: play.card_value for play in event.plays}

    revealed = state.revealed_trick
    if revealed is None:
        return {}
    return {play.player_id: play.card_value for play in revealed.plays}


def _current_cards_revealed_event(
    state: ClientState,
) -> PresentationCardsRevealed | None:
    step = state.current_presentation_step
    if step is None:
        return None
    event = step.event
    return event if isinstance(event, PresentationCardsRevealed) else None


def _own_revealed_card_value(
    state: ClientState,
    revealed_values: dict[PlayerID, int],
) -> int | None:
    if _current_cards_revealed_event(state) is None:
        return None
    own_player_id = state.own_player_id
    if own_player_id is None:
        return None
    return revealed_values.get(own_player_id)


def _completed_card_values_by_player(state: ClientState) -> dict[PlayerID, int]:
    completed: dict[PlayerID, int] = {}
    for step in state.presentation_steps:
        event = step.event
        if isinstance(event, PresentationCardPlaced | PresentationOverflowResolved):
            completed[event.player_id] = event.card_value
        elif isinstance(event, PresentationRowTaken):
            completed[event.player_id] = event.replacement_card_value
    return completed


def _build_hand(
    state: ClientState,
    *,
    selected_card_value: int | None,
    hidden_card_values: frozenset[int],
) -> tuple[VisualHandCard, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()
    return tuple(
        VisualHandCard(
            card_value=card.value,
            bullheads=card.bullheads,
            visible=card.value not in hidden_card_values,
            emphasis=(
                "selected"
                if card.value == selected_card_value and card.value not in hidden_card_values
                else "none"
            ),
        )
        for card in player_state.hand
    )


def _build_cards_revealed_panel(
    state: ClientState,
) -> VisualPresentationPanel | None:
    event = _current_cards_revealed_event(state)
    if event is None:
        return None

    return VisualPresentationPanel(
        headline="Karten aufgedeckt",
        details=_presentation_details(state),
        card_values=tuple(play.card_value for play in event.plays),
    )


def _presentation_details(state: ClientState) -> tuple[str, ...]:
    return tuple(
        format_presentation_event(step.event)
        for step in state.pending_presentation_steps[:3]
    )


def _build_interaction(
    state: ClientState,
    hand: tuple[VisualHandCard, ...],
) -> VisualInteraction:
    if state.pending_presentation_steps:
        return VisualInteraction(can_advance_presentation=True)

    if state.pending_action == PendingAction.CHOOSE_CARD:
        return VisualInteraction(
            selectable_card_values=frozenset(
                card.card_value for card in hand if card.visible
            )
        )

    if state.pending_action == PendingAction.CHOOSE_ROW and state.player_state is not None:
        return VisualInteraction(
            selectable_row_ids=frozenset(
                state.player_state.get_selectable_row_ids_for_choose_row()
            )
        )

    return VisualInteraction()


def _build_status(
    state: ClientState,
    *,
    public_state: PublicState | None,
    players: tuple[VisualPlayer, ...],
    last_action_summary: str,
) -> VisualStatus:
    own_player = next((player for player in players if player.is_self), None)
    player_name = own_player.name if own_player is not None else "-"
    phase = public_state.phase_info.phase.value if public_state is not None else "-"
    primary_line = (
        f"{player_name}  |  Phase: {phase}  |  Aktion: {state.pending_action.value}"
    )

    flash = state.flash_message
    secondary_line = flash.text if flash is not None else last_action_summary
    message_level = flash.level if flash is not None else "normal"

    hand_prompt = None
    if public_state is not None and public_state.phase_info.pending_card is not None:
        hand_prompt = f"Reihe für Karte {public_state.phase_info.pending_card.value} wählen"

    return VisualStatus(
        primary_line=primary_line,
        secondary_line=secondary_line,
        message_level=message_level,
        hand_prompt=hand_prompt,
    )
