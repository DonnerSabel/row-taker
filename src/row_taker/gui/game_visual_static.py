from __future__ import annotations

from collections.abc import Mapping

from row_taker.client.core_state import PendingAction
from row_taker.client.presentation_events import PresentationCardsRevealed
from row_taker.client.state import ClientState
from row_taker.engine.game.models import PlayerID, RowID
from row_taker.engine.game.state import PublicState
from row_taker.gui.game_visual_invariants import assert_selectable_objects_are_visible
from row_taker.gui.game_visual_state import (
    GameVisualState,
    RowEmphasis,
    VisualCard,
    VisualHandCard,
    VisualInteraction,
    VisualPlayer,
    VisualPresentationPanel,
    VisualRow,
    VisualStatus,
)


def build_stable_game_visual_state(
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
    event = current_cards_revealed_event(state)
    if event is not None:
        return {play.player_id: play.card_value for play in event.plays}

    revealed = state.revealed_trick
    if revealed is None:
        return {}
    return {play.player_id: play.card_value for play in revealed.plays}


def current_cards_revealed_event(
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
    if current_cards_revealed_event(state) is None:
        return None
    own_player_id = state.own_player_id
    if own_player_id is None:
        return None
    return revealed_values.get(own_player_id)


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
