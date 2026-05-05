from __future__ import annotations

import pygame

from row_taker.gui.assets import DEFAULT_GUI_ASSETS
from row_taker.gui.menu_layout import DEFAULT_MENU_LAYOUT, MenuLayoutConfig, header_footer_layout
from row_taker.gui.theme import DEFAULT_THEME, GuiTheme
from row_taker.gui.widgets import centered_text_position, draw_overlay_panel, draw_panel, draw_vertical_gradient
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import PrimitiveDrawer

THEME = DEFAULT_THEME
PALETTE = THEME.palette


def draw_menu_background(screen: pygame.Surface, *, theme: GuiTheme = THEME) -> None:
    background = DEFAULT_GUI_ASSETS.scaled_connect_background(screen.get_width(), screen.get_height())
    if background is None:
        draw_vertical_gradient(screen, theme=theme)
    else:
        screen.blit(background, (0, 0))

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill(pygame.Color(0, 0, 0, 146))
    screen.blit(overlay, (0, 0))

    top_overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(
        top_overlay,
        pygame.Color(4, 10, 20, 92),
        pygame.Rect(0, 0, screen.get_width(), screen.get_height() // 3),
    )
    screen.blit(top_overlay, (0, 0))


def draw_menu_header(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    *,
    title: str,
    subtitle: str,
    theme: GuiTheme = THEME,
    config: MenuLayoutConfig = DEFAULT_MENU_LAYOUT,
) -> None:
    rect = header_footer_layout(layout, config=config).header_rect
    draw_overlay_panel(screen, rect, radius=20, alpha=58, theme=theme)
    drawer.draw_text(screen, title, (rect.left + 24, rect.top + 10), role="title")
    drawer.draw_text(screen, subtitle, (rect.left + 24, rect.top + 42), role="body", color=theme.palette.text_muted)


def draw_menu_footer(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    *,
    text: str,
    is_error: bool = False,
    theme: GuiTheme = THEME,
    config: MenuLayoutConfig = DEFAULT_MENU_LAYOUT,
) -> None:
    rect = header_footer_layout(layout, config=config).footer_rect
    draw_overlay_panel(screen, rect, radius=20, alpha=52, theme=theme)
    color = theme.palette.danger if is_error else theme.palette.text_muted
    drawer.draw_text(
        screen,
        text,
        centered_text_position(drawer, text, rect, role="body"),
        role="body",
        color=color,
    )


def draw_menu_panel(
    screen: pygame.Surface,
    rect: pygame.Rect,
    *,
    theme: GuiTheme = THEME,
    alpha: int = 228,
) -> None:
    draw_panel(
        screen,
        rect,
        radius=theme.spacing.large_panel_radius,
        fill=theme.palette.panel_fill_strong,
        border=theme.palette.panel_border_soft,
        alpha=alpha,
        theme=theme,
    )


def draw_text_input(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    value: str,
    placeholder: str = "",
    active: bool = False,
    hovered: bool = False,
    selected: bool = False,
    theme: GuiTheme = THEME,
) -> None:
    palette = theme.palette
    fill = palette.panel_fill
    if hovered:
        fill = fill.lerp(palette.text_primary, 0.04)
    border = palette.accent_hover if active else palette.panel_border
    border_width = 2 if active else 1

    pygame.draw.rect(screen, fill, rect, border_radius=14)
    pygame.draw.rect(screen, border, rect, width=border_width, border_radius=14)

    display_value = value if value else placeholder
    text_color = palette.text_primary if value else palette.text_muted
    text_pos = (rect.left + 16, rect.top + 14)

    if selected and value:
        _draw_text_selection(screen, drawer, rect, value)

    drawer.draw_text(screen, display_value, text_pos, role="body", color=text_color)

    if active and not selected:
        _draw_text_cursor(screen, drawer, rect, display_value, theme=theme)


def _draw_text_selection(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    text: str,
) -> None:
    font = drawer._font_for_role("body")
    text_width, text_height = font.size(text)
    selection_rect = pygame.Rect(rect.left + 12, rect.top + 8, text_width + 10, max(30, text_height + 8))
    selection_surface = pygame.Surface(selection_rect.size, pygame.SRCALPHA)
    selection_surface.fill(pygame.Color(80, 132, 212, 120))
    screen.blit(selection_surface, selection_rect)


def _draw_text_cursor(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    text: str,
    *,
    theme: GuiTheme,
) -> None:
    font = drawer._font_for_role("body")
    text_width = font.size(text)[0]
    cursor_x = min(rect.right - 16, rect.left + 16 + text_width + 2)
    cursor_rect = pygame.Rect(cursor_x, rect.top + 10, 2, rect.height - 20)
    pygame.draw.rect(screen, theme.palette.accent_hover, cursor_rect)
