from __future__ import annotations

import pytest

from row_taker.gui.board_layout import compute_board_geometry, hand_card_placements


@pytest.mark.parametrize(
    "window_size",
    (
        (980, 720),
        (1024, 768),
        (1280, 720),
        (1600, 900),
    ),
)
def test_new_game_regions_fit_inside_the_window(window_size: tuple[int, int]) -> None:
    geometry = compute_board_geometry(
        window_size,
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )

    assert geometry.window_rect.contains(geometry.play_area_rect)
    assert geometry.window_rect.contains(geometry.sidebar_rect)
    assert geometry.play_area_rect.right < geometry.sidebar_rect.left
    assert geometry.play_area_rect.width >= 460

    for section in (
        geometry.sidebar_header_rect,
        geometry.opponent_list_rect,
        geometry.presentation_rect,
        geometry.own_player_rect,
    ):
        assert geometry.sidebar_rect.contains(section)

    assert geometry.sidebar_header_rect.bottom < geometry.opponent_list_rect.top
    assert geometry.opponent_list_rect.bottom < geometry.presentation_rect.top
    assert geometry.presentation_rect.bottom < geometry.own_player_rect.top


@pytest.mark.parametrize(
    "window_size",
    (
        (980, 720),
        (1024, 768),
        (1280, 720),
        (1600, 900),
    ),
)
def test_five_opponent_tiles_keep_text_separate_and_cards_inside_sidebar(
    window_size: tuple[int, int],
) -> None:
    geometry = compute_board_geometry(
        window_size,
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )

    assert len(geometry.opponent_tiles) == 5
    for tile in geometry.opponent_tiles:
        assert geometry.opponent_list_rect.contains(tile.tile_rect)
        assert tile.tile_rect.contains(tile.info_rect)
        assert geometry.sidebar_rect.contains(tile.card_placement.rect)

    for upper, lower in zip(geometry.opponent_tiles, geometry.opponent_tiles[1:], strict=False):
        assert upper.tile_rect.bottom == lower.tile_rect.top
        assert not upper.info_rect.colliderect(lower.info_rect)

    card_rects = [tile.card_placement.rect for tile in geometry.opponent_tiles]
    assert any(
        upper.colliderect(lower)
        for upper, lower in zip(card_rects, card_rects[1:], strict=False)
    )


@pytest.mark.parametrize("opponent_count", range(6))
def test_opponent_tile_count_matches_player_count(opponent_count: int) -> None:
    geometry = compute_board_geometry(
        (1280, 720),
        row_count=4,
        hand_card_count=10,
        opponent_count=opponent_count,
    )

    assert len(geometry.opponent_tiles) == opponent_count


def test_own_player_tile_has_card_and_info_inside_own_section() -> None:
    geometry = compute_board_geometry(
        (980, 720),
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )
    own_tile = geometry.own_player_tile

    assert own_tile.tile_rect == geometry.own_player_rect
    assert geometry.own_player_rect.contains(own_tile.info_rect)
    assert geometry.own_player_rect.contains(own_tile.card_placement.rect)
    assert own_tile.card_placement.rect.right < own_tile.info_rect.left


def test_remaining_legacy_geometry_stays_available_during_incremental_migration() -> None:
    geometry = compute_board_geometry(
        (1280, 720),
        row_count=4,
        hand_card_count=10,
        opponent_count=3,
    )

    assert geometry.main_play_rect.width > 0
    assert geometry.stats_rect.width > 0
    assert geometry.hand_rect.width > 0
    assert len(geometry.opponent_slots) == 3
    assert geometry.overlay_rect.width > 0


@pytest.mark.parametrize(
    "window_size",
    (
        (980, 720),
        (1024, 768),
        (1280, 720),
        (1600, 900),
    ),
)
def test_hand_and_hand_cards_stay_left_of_sidebar(
    window_size: tuple[int, int],
) -> None:
    geometry = compute_board_geometry(
        window_size,
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )

    assert geometry.play_area_rect.contains(geometry.hand_rect)
    assert geometry.hand_rect.right < geometry.sidebar_rect.left
    for placement in hand_card_placements(geometry, card_count=10):
        assert not placement.rect.colliderect(geometry.sidebar_rect)
