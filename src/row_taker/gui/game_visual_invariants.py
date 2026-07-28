from __future__ import annotations

from collections import Counter

from row_taker.engine.game.state import PublicState
from row_taker.gui.game_visual_state import GameVisualState


def assert_visual_matches_public_state(
    visual_state: GameVisualState,
    public_state: PublicState,
) -> None:
    """Assert logical rows and public player data independent of visual ordering."""

    visual_rows = {
        row.row_id: tuple((card.card_value, card.bullheads) for card in row.cards)
        for row in visual_state.rows
    }
    public_rows = {
        row.row_id: tuple((card.value, card.bullheads) for card in row.cards)
        for row in public_state.rows
    }
    if visual_rows != public_rows:
        raise AssertionError(
            "visual rows do not match the public state: "
            f"visual={visual_rows!r}, public={public_rows!r}"
        )

    visual_players = {
        player.player_id: (player.name, player.score, player.hand_count)
        for player in visual_state.players
    }
    public_players = {
        player.player_id: (player.name, player.score, player.hand_count)
        for player in public_state.players
    }
    if visual_players != public_players:
        raise AssertionError(
            "visual players do not match the public state: "
            f"visual={visual_players!r}, public={public_players!r}"
        )


def assert_selectable_objects_are_visible(visual_state: GameVisualState) -> None:
    visible_card_values = {
        card.card_value for card in visual_state.hand if card.visible
    }
    missing_cards = (
        visual_state.interaction.selectable_card_values - visible_card_values
    )
    if missing_cards:
        raise AssertionError(
            f"selectable hand cards are not visible: {sorted(missing_cards)!r}"
        )

    visible_row_ids = {row.row_id for row in visual_state.rows}
    missing_rows = visual_state.interaction.selectable_row_ids - visible_row_ids
    if missing_rows:
        raise AssertionError(
            f"selectable rows are not visible: {sorted(map(str, missing_rows))!r}"
        )


def assert_motion_anchors_are_resolvable(visual_state: GameVisualState) -> None:
    players_by_id = {player.player_id: player for player in visual_state.players}
    rows_by_id = {row.row_id: row for row in visual_state.rows}

    for moving_card in visual_state.moving_cards:
        source = moving_card.source
        if source.player_id not in players_by_id:
            raise AssertionError(
                f"moving-card source player is missing: {source.player_id!r}"
            )
        # The server may already have removed the own played card from the
        # current PlayerState. The renderer then resolves the semantic source
        # through the stable hand-area fallback.
        if source.card_value != moving_card.card_value:
            raise AssertionError(
                "moving-card source value differs from the moving card: "
                f"source={source.card_value}, card={moving_card.card_value}"
            )

        target = moving_card.target
        row = rows_by_id.get(target.row_id)
        if row is None:
            raise AssertionError(
                f"moving-card target row is missing: {target.row_id!r}"
            )
        if not 0 <= target.card_index <= len(row.cards):
            raise AssertionError(
                "moving-card target index is outside the row layout: "
                f"row={target.row_id!r}, index={target.card_index}, "
                f"card_count={len(row.cards)}"
            )


def assert_no_visible_game_card_is_duplicated(
    visual_state: GameVisualState,
) -> None:
    """Reject duplicate visible game objects; panel thumbnails are excluded."""

    visible_values: list[int] = []
    visible_values.extend(
        card.card_value for row in visual_state.rows for card in row.cards
    )
    visible_values.extend(
        card.card_value for card in visual_state.hand if card.visible
    )
    visible_values.extend(
        player.staged_card_value
        for player in visual_state.players
        if player.staged_card_value is not None
    )
    visible_values.extend(card.card_value for card in visual_state.moving_cards)

    duplicates = sorted(
        value for value, count in Counter(visible_values).items() if count > 1
    )
    if duplicates:
        raise AssertionError(
            f"visible game cards are duplicated: {duplicates!r}"
        )
