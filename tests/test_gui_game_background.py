from __future__ import annotations

import pygame

from row_taker.gui.board_layout import compute_board_geometry
from row_taker.gui.rendering.game_renderer import (
    PALETTE,
    SIDEBAR_BORDER_WIDTH,
    _draw_game_background,
    _draw_sidebar_frame,
)


def test_game_background_uses_flat_board_and_sidebar_fills() -> None:
    geometry = compute_board_geometry(
        (980, 720),
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )
    screen = pygame.Surface(geometry.window_rect.size)

    _draw_game_background(screen, geometry)

    assert screen.get_at(geometry.play_area_rect.center) == PALETTE.board_fallback
    assert screen.get_at(geometry.sidebar_rect.center) == PALETTE.panel_fill_strong


def test_sidebar_frame_marks_the_complete_sidebar_boundary() -> None:
    geometry = compute_board_geometry(
        (980, 720),
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )
    screen = pygame.Surface(geometry.window_rect.size)
    _draw_game_background(screen, geometry)

    _draw_sidebar_frame(screen, geometry.sidebar_rect)

    border_point = (
        geometry.sidebar_rect.left + SIDEBAR_BORDER_WIDTH // 2,
        geometry.sidebar_rect.centery,
    )
    inner_point = (
        geometry.sidebar_rect.left + SIDEBAR_BORDER_WIDTH + 2,
        geometry.sidebar_rect.centery,
    )
    outside_point = (geometry.sidebar_rect.left - 1, geometry.sidebar_rect.centery)

    assert screen.get_at(border_point) == PALETTE.text_primary
    assert screen.get_at(inner_point) == PALETTE.panel_fill_strong
    assert screen.get_at(outside_point) == PALETTE.board_fallback
