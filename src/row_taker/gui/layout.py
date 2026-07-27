from __future__ import annotations

from dataclasses import dataclass

import pygame

MIN_WINDOW_WIDTH = 980
MIN_WINDOW_HEIGHT = 720
SIDEBAR_WIDTH = 300
HEADER_HEIGHT = 72
FOOTER_HEIGHT = 76
PANEL_GAP = 12
PANEL_PADDING = 12


@dataclass(frozen=True, slots=True)
class GuiLayout:
    window_rect: pygame.Rect
    header_rect: pygame.Rect
    main_rect: pygame.Rect
    sidebar_rect: pygame.Rect
    footer_rect: pygame.Rect
    main_top_rect: pygame.Rect
    main_bottom_rect: pygame.Rect


def compute_layout(window_width: int, window_height: int) -> GuiLayout:
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

    split_height = max(180, (content_height - PANEL_GAP) // 2)
    main_top_rect = pygame.Rect(main_rect.left, main_rect.top, main_rect.width, split_height)
    main_bottom_height = main_rect.height - split_height - PANEL_GAP
    main_bottom_rect = pygame.Rect(
        main_rect.left,
        main_top_rect.bottom + PANEL_GAP,
        main_rect.width,
        main_bottom_height,
    )

    return GuiLayout(
        window_rect=window_rect,
        header_rect=header_rect,
        main_rect=main_rect,
        sidebar_rect=sidebar_rect,
        footer_rect=footer_rect,
        main_top_rect=main_top_rect,
        main_bottom_rect=main_bottom_rect,
    )
