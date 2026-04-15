from __future__ import annotations

from dataclasses import dataclass

import pygame

MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 650
SIDEBAR_WIDTH = 280
HEADER_HEIGHT = 72
FOOTER_HEIGHT = 76
PANEL_GAP = 12
PANEL_PADDING = 12


@dataclass(frozen=True, slots=True)
class DemoLayout:
    window_rect: pygame.Rect
    header_rect: pygame.Rect
    main_rect: pygame.Rect
    sidebar_rect: pygame.Rect
    footer_rect: pygame.Rect


def compute_layout(window_width: int, window_height: int) -> DemoLayout:
    width = max(window_width, MIN_WINDOW_WIDTH)
    height = max(window_height, MIN_WINDOW_HEIGHT)

    window_rect = pygame.Rect(0, 0, width, height)
    header_rect = pygame.Rect(PANEL_GAP, PANEL_GAP, width - 2 * PANEL_GAP, HEADER_HEIGHT)
    footer_rect = pygame.Rect(
        PANEL_GAP,
        height - FOOTER_HEIGHT - PANEL_GAP,
        width - 2 * PANEL_GAP,
        FOOTER_HEIGHT,
    )

    content_top = header_rect.bottom + PANEL_GAP
    content_bottom = footer_rect.top - PANEL_GAP
    content_height = content_bottom - content_top
    content_width = width - 2 * PANEL_GAP
    sidebar_width = min(SIDEBAR_WIDTH, content_width // 3)
    main_width = content_width - sidebar_width - PANEL_GAP

    main_rect = pygame.Rect(PANEL_GAP, content_top, main_width, content_height)
    sidebar_rect = pygame.Rect(main_rect.right + PANEL_GAP, content_top, sidebar_width, content_height)

    return DemoLayout(
        window_rect=window_rect,
        header_rect=header_rect,
        main_rect=main_rect,
        sidebar_rect=sidebar_rect,
        footer_rect=footer_rect,
    )
