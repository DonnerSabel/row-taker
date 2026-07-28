from __future__ import annotations

import pytest

from row_taker.gui.board_layout import (
    DEFAULT_BOARD_LAYOUT,
    compute_board_geometry,
    hand_card_placements,
)


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
        upper.colliderect(lower) for upper, lower in zip(card_rects, card_rects[1:], strict=False)
    )


@pytest.mark.parametrize(
    "window_size",
    (
        (980, 720),
        (1024, 768),
        (1280, 720),
        (1600, 900),
    ),
)
@pytest.mark.parametrize("opponent_count", range(1, 6))
def test_opponent_tiles_have_equal_height_and_fixed_card_offsets(
    window_size: tuple[int, int],
    opponent_count: int,
) -> None:
    geometry = compute_board_geometry(
        window_size,
        row_count=4,
        hand_card_count=10,
        opponent_count=opponent_count,
    )

    tiles = geometry.opponent_tiles
    assert len({tile.tile_rect.height for tile in tiles}) == 1
    assert len({tile.tile_rect.width for tile in tiles}) == 1
    assert tiles[0].tile_rect.height <= DEFAULT_BOARD_LAYOUT.player_tile_preferred_height_px

    for tile in tiles:
        card_rect = tile.card_placement.rect
        assert card_rect.left - tile.tile_rect.left == (
            DEFAULT_BOARD_LAYOUT.player_tile_card_left_offset_px
        )
        assert card_rect.top - tile.tile_rect.top == (
            DEFAULT_BOARD_LAYOUT.player_tile_card_top_offset_px
        )
        assert geometry.opponent_list_rect.contains(card_rect)

    for upper, lower in zip(tiles, tiles[1:], strict=False):
        assert upper.tile_rect.bottom == lower.tile_rect.top

    assert tiles[-1].tile_rect.bottom <= geometry.opponent_list_rect.bottom


def test_own_player_card_uses_the_same_fixed_offsets_as_opponents() -> None:
    geometry = compute_board_geometry(
        (980, 720),
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )
    own_tile = geometry.own_player_tile
    own_card = own_tile.card_placement.rect

    assert own_card.left - own_tile.tile_rect.left == (
        DEFAULT_BOARD_LAYOUT.player_tile_card_left_offset_px
    )
    assert own_card.top - own_tile.tile_rect.top == (
        DEFAULT_BOARD_LAYOUT.player_tile_card_top_offset_px
    )


def test_few_opponents_do_not_stretch_tiles_to_fill_the_list() -> None:
    geometry = compute_board_geometry(
        (980, 720),
        row_count=4,
        hand_card_count=10,
        opponent_count=2,
    )

    assert all(
        tile.tile_rect.height == DEFAULT_BOARD_LAYOUT.player_tile_preferred_height_px
        for tile in geometry.opponent_tiles
    )
    assert geometry.opponent_tiles[-1].tile_rect.bottom < geometry.opponent_list_rect.bottom


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


def test_rows_and_hand_use_only_the_artwork_independent_play_area() -> None:
    geometry = compute_board_geometry(
        (1280, 720),
        row_count=4,
        hand_card_count=10,
        opponent_count=3,
    )

    assert geometry.play_area_rect.contains(geometry.row_area_rect)
    assert geometry.play_area_rect.contains(geometry.hand_rect)
    assert geometry.row_area_rect.bottom < geometry.hand_rect.top
    assert all(geometry.row_area_rect.contains(column) for column in geometry.row_columns)


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
