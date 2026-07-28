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
    visible_card_values = {card.card_value for card in visual_state.hand if card.visible}
    missing_cards = visual_state.interaction.selectable_card_values - visible_card_values
    if missing_cards:
        raise AssertionError(f"selectable hand cards are not visible: {sorted(missing_cards)!r}")

    visible_row_ids = {row.row_id for row in visual_state.rows}
    missing_rows = visual_state.interaction.selectable_row_ids - visible_row_ids
    if missing_rows:
        raise AssertionError(f"selectable rows are not visible: {sorted(map(str, missing_rows))!r}")


def assert_motion_anchors_are_resolvable(visual_state: GameVisualState) -> None:
    players_by_id = {player.player_id: player for player in visual_state.players}
    rows_by_id = {row.row_id: row for row in visual_state.rows}

    for moving_card in visual_state.moving_cards:
        source = moving_card.source
        if source.player_id not in players_by_id:
            raise AssertionError(f"moving-card source player is missing: {source.player_id!r}")
        if source.card_value != moving_card.card_value:
            raise AssertionError(
                "moving-card source value differs from the moving card: "
                f"source={source.card_value}, card={moving_card.card_value}"
            )

        target = moving_card.target
        row = rows_by_id.get(target.row_id)
        if row is None:
            raise AssertionError(f"moving-card target row is missing: {target.row_id!r}")
        if not 0 <= target.card_index <= len(row.cards):
            raise AssertionError(
                "moving-card target index is outside the row layout: "
                f"row={target.row_id!r}, index={target.card_index}, "
                f"card_count={len(row.cards)}"
            )


def assert_player_card_locations_are_consistent(
    visual_state: GameVisualState,
) -> None:
    """Assert unique player roles and one visible card location per player."""

    player_ids = [player.player_id for player in visual_state.players]
    duplicate_player_ids = sorted(
        (player_id for player_id, count in Counter(player_ids).items() if count > 1),
        key=str,
    )
    if duplicate_player_ids:
        raise AssertionError(f"visual player ids are duplicated: {duplicate_player_ids!r}")

    own_players = [player.player_id for player in visual_state.players if player.is_self]
    if len(own_players) > 1:
        raise AssertionError(f"visual state contains multiple own players: {own_players!r}")

    active_players = [
        player.player_id for player in visual_state.players if player.emphasis == "active"
    ]
    if len(active_players) > 1:
        raise AssertionError(f"visual state contains multiple active players: {active_players!r}")

    moving_source_ids = [card.source.player_id for card in visual_state.moving_cards]
    duplicate_moving_sources = sorted(
        (player_id for player_id, count in Counter(moving_source_ids).items() if count > 1),
        key=str,
    )
    if duplicate_moving_sources:
        raise AssertionError(
            f"multiple moving cards use the same player source: {duplicate_moving_sources!r}"
        )

    moving_source_id_set = set(moving_source_ids)
    visible_hand_values = {card.card_value for card in visual_state.hand if card.visible}
    for player in visual_state.players:
        staged_card_value = player.staged_card_value
        if staged_card_value is None:
            continue
        if player.player_id in moving_source_id_set:
            raise AssertionError(
                "player card is visible both in the tile and in motion: "
                f"player={player.player_id!r}, card={staged_card_value}"
            )
        if player.is_self and staged_card_value in visible_hand_values:
            raise AssertionError(
                "own staged card is still visible in the hand: "
                f"player={player.player_id!r}, card={staged_card_value}"
            )

    players_by_id = {player.player_id: player for player in visual_state.players}
    for moving_card in visual_state.moving_cards:
        source_player = players_by_id.get(moving_card.source.player_id)
        if source_player is None:
            continue
        if source_player.staged_card_value is not None:
            raise AssertionError(
                "moving card still exists in its player tile: "
                f"player={source_player.player_id!r}, "
                f"card={moving_card.card_value}"
            )
        if source_player.is_self and moving_card.card_value in visible_hand_values:
            raise AssertionError(
                "moving own card is still visible in the hand: "
                f"player={source_player.player_id!r}, "
                f"card={moving_card.card_value}"
            )


def assert_no_visible_game_card_is_duplicated(
    visual_state: GameVisualState,
) -> None:
    """Reject duplicate cards across rows, hand, player tiles, and motions."""

    visible_values: list[int] = []
    visible_values.extend(card.card_value for row in visual_state.rows for card in row.cards)
    visible_values.extend(card.card_value for card in visual_state.hand if card.visible)
    visible_values.extend(
        player.staged_card_value
        for player in visual_state.players
        if player.staged_card_value is not None
    )
    visible_values.extend(card.card_value for card in visual_state.moving_cards)

    duplicates = sorted(value for value, count in Counter(visible_values).items() if count > 1)
    if duplicates:
        raise AssertionError(f"visible game cards are duplicated: {duplicates!r}")


def assert_visual_state_is_consistent(visual_state: GameVisualState) -> None:
    """Assert all frontend-independent invariants of one complete visual state."""

    assert_selectable_objects_are_visible(visual_state)
    assert_motion_anchors_are_resolvable(visual_state)
    assert_player_card_locations_are_consistent(visual_state)
    assert_no_visible_game_card_is_duplicated(visual_state)
