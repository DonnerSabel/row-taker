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
    draw_opponent_tiles,
    draw_own_player_tile,
    draw_sidebar_header,
    player_staged_card_rects,
)
from row_taker.gui.theme import DEFAULT_THEME

PALETTE = DEFAULT_THEME.palette
SIDEBAR_BORDER_WIDTH = 3


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
    # Stable board content forms the back layer.
    draw_rows(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
        assets,
        presentation_clock,
    )

    # Player tiles belong behind the hand and every animated card.
    draw_opponent_tiles(
        screen,
        drawer,
        geometry,
        visual_state,
        assets,
    )
    draw_own_player_tile(
        screen,
        drawer,
        geometry,
        visual_state,
        assets,
    )
    draw_hand(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
        assets,
    )

    # Motion is transient game content. Sidebar text is deliberately drawn
    # afterwards so a flight path can never make instructions unreadable.
    draw_presentation_card_motion(
        screen,
        drawer,
        geometry,
        visual_state,
        assets,
        player_staged_card_rects=player_staged_card_rects(
            visual_state,
            geometry,
        ),
    )
    draw_sidebar_header(
        screen,
        drawer,
        geometry,
        visual_state,
    )

    # Draw the boundary last so accidental overflows remain immediately visible.
    _draw_sidebar_frame(screen, geometry.sidebar_rect)


def _draw_game_background(
    screen: pygame.Surface,
    geometry: BoardGeometry,
) -> None:
    """Draw the artwork-independent game background.

    Flat fills keep geometry independent from a fixed-size background image.
    A later responsive design can replace these fills without changing layout.
    """

    screen.fill(PALETTE.board_fallback)
    pygame.draw.rect(screen, PALETTE.panel_fill_strong, geometry.sidebar_rect)


def _draw_sidebar_frame(
    screen: pygame.Surface,
    sidebar_rect: pygame.Rect,
) -> None:
    """Draw the sidebar boundary last so overflows stay immediately visible."""

    pygame.draw.rect(
        screen,
        PALETTE.text_primary,
        sidebar_rect,
        width=SIDEBAR_BORDER_WIDTH,
    )
