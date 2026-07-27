from __future__ import annotations

import pygame

from row_taker.gui.animation import AnimationClock
from row_taker.gui.assets import DEFAULT_GUI_ASSETS, GuiAssets
from row_taker.gui.board_layout import BoardGeometry
from row_taker.gui.game_interaction import GameScreenTargets
from row_taker.gui.game_visual_state import GameVisualState
from row_taker.gui.presentation_renderer import draw_presentation_card_motion
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.rendering.board_renderer import draw_rows
from row_taker.gui.rendering.game_hud_renderer import (
    draw_hand,
    draw_opponent_slots,
    draw_stats_field,
    draw_status_overlay,
    opponent_staged_card_rects,
)


def render_game_screen(
    screen: pygame.Surface,
    *,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    presentation_elapsed_frames: int,
    assets: GuiAssets = DEFAULT_GUI_ASSETS,
) -> None:
    """Render one complete game frame through the production render pipeline."""

    presentation_clock = AnimationClock(presentation_elapsed_frames)

    _draw_full_background(screen, geometry.window_rect, assets)
    draw_rows(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
        assets,
        presentation_clock,
    )
    draw_opponent_slots(
        screen,
        drawer,
        geometry,
        visual_state,
        assets,
        presentation_clock,
    )
    draw_hand(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
        assets,
    )
    draw_presentation_card_motion(
        screen,
        drawer,
        geometry,
        visual_state,
        assets,
        opponent_staged_card_rects=opponent_staged_card_rects(
            visual_state,
            geometry,
        ),
    )
    draw_stats_field(screen, drawer, geometry, visual_state)
    draw_status_overlay(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
        assets,
        presentation_clock,
    )


def _draw_full_background(
    screen: pygame.Surface,
    window_rect: pygame.Rect,
    assets: GuiAssets,
) -> None:
    board = assets.scaled_board_image_full(window_rect.width, window_rect.height)
    if board is None:
        screen.fill((18, 84, 38))
        return

    # board.png is the full background. No cropping, aspect ratio ignored.
    screen.blit(board, window_rect.topleft)
