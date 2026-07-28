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
    draw_stats_field,
    draw_status_overlay,
    opponent_staged_card_rects,
)
from row_taker.gui.theme import DEFAULT_THEME

PALETTE = DEFAULT_THEME.palette
SIDEBAR_DEBUG_BORDER_WIDTH = 3


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

    _draw_game_background(screen, geometry)
    draw_rows(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
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
    _draw_sidebar_debug_frame(screen, geometry.sidebar_rect)


def _draw_game_background(
    screen: pygame.Surface,
    geometry: BoardGeometry,
) -> None:
    """Draw the temporary artwork-independent game background.

    The polished ``board.png`` no longer matches the widened sidebar. Until a
    responsive background design exists, flat fills make the new layout easy
    to inspect without coupling geometry back to artwork.
    """

    screen.fill(PALETTE.board_fallback)
    pygame.draw.rect(screen, PALETTE.panel_fill_strong, geometry.sidebar_rect)


def _draw_sidebar_debug_frame(
    screen: pygame.Surface,
    sidebar_rect: pygame.Rect,
) -> None:
    """Draw the sidebar boundary last so overflows stay immediately visible."""

    pygame.draw.rect(
        screen,
        PALETTE.text_primary,
        sidebar_rect,
        width=SIDEBAR_DEBUG_BORDER_WIDTH,
    )
