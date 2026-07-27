from __future__ import annotations

from row_taker.client.core_state import PendingAction
from row_taker.client.state import ClientState
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.state import PublicState
from row_taker.gui.game_visual_state import (
    GameVisualState,
    VisualCard,
    VisualHandCard,
    VisualInteraction,
    VisualPlayer,
    VisualRow,
    VisualStatus,
)


def build_game_visual_state(
    state: ClientState,
    *,
    last_action_summary: str,
    public_state_override: PublicState | None = None,
) -> GameVisualState:
    """Translate client semantics into the complete stable game-screen model."""

    public_state = public_state_override or state.public_state
    rows = _build_rows(public_state)
    players = _build_players(state, public_state)
    hand = _build_hand(state)
    interaction = _build_interaction(state, hand)
    status = _build_status(
        state,
        public_state=public_state,
        players=players,
        last_action_summary=last_action_summary,
    )
    return GameVisualState(
        rows=rows,
        players=players,
        hand=hand,
        interaction=interaction,
        status=status,
    )


def _build_rows(public_state: PublicState | None) -> tuple[VisualRow, ...]:
    if public_state is None:
        return ()

    rows = tuple(
        VisualRow(
            row_id=row.row_id,
            cards=tuple(
                VisualCard(card_value=card.value, bullheads=card.bullheads)
                for card in row.cards
            ),
        )
        for row in public_state.rows
    )
    return tuple(sorted(rows, key=_visual_row_sort_key))


def _visual_row_sort_key(row: VisualRow) -> tuple[int, str]:
    last_value = row.cards[-1].card_value if row.cards else -1
    return (last_value, str(row.row_id))


def _build_players(
    state: ClientState,
    public_state: PublicState | None,
) -> tuple[VisualPlayer, ...]:
    if public_state is None:
        return ()

    staged_values = _revealed_card_values_by_player(state)
    return tuple(
        VisualPlayer(
            player_id=player.player_id,
            name=player.name,
            score=player.score,
            hand_count=player.hand_count,
            is_self=player.player_id == state.own_player_id,
            staged_card_value=staged_values.get(player.player_id),
        )
        for player in public_state.players
    )


def _revealed_card_values_by_player(state: ClientState) -> dict[PlayerID, int]:
    revealed = state.revealed_trick
    if revealed is None:
        return {}
    return {play.player_id: play.card_value for play in revealed.plays}


def _build_hand(state: ClientState) -> tuple[VisualHandCard, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()
    return tuple(
        VisualHandCard(card_value=card.value, bullheads=card.bullheads)
        for card in player_state.hand
    )


def _build_interaction(
    state: ClientState,
    hand: tuple[VisualHandCard, ...],
) -> VisualInteraction:
    if state.pending_presentation_events:
        return VisualInteraction(can_advance_presentation=True)

    if state.pending_action == PendingAction.CHOOSE_CARD:
        return VisualInteraction(
            selectable_card_values=frozenset(card.card_value for card in hand if card.visible)
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
