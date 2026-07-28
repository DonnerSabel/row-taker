from __future__ import annotations

from typing import Literal

import pygame

from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.theme import DEFAULT_THEME, GuiTheme

ButtonVariant = Literal["primary", "success", "danger", "neutral"]


def draw_vertical_gradient(
    surface: pygame.Surface,
    *,
    top: pygame.Color | None = None,
    bottom: pygame.Color | None = None,
    theme: GuiTheme = DEFAULT_THEME,
) -> None:
    palette = theme.palette
    top_color = top or palette.background_top
    bottom_color = bottom or palette.background_bottom
    height = max(1, surface.get_height())
    for y in range(height):
        t = y / height
        color = top_color.lerp(bottom_color, t)
        pygame.draw.line(surface, color, (0, y), (surface.get_width(), y))


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    radius: int | None = None,
    fill: pygame.Color | None = None,
    border: pygame.Color | None = None,
    border_width: int = 1,
    alpha: int | None = None,
    theme: GuiTheme = DEFAULT_THEME,
) -> None:
    palette = theme.palette
    spacing = theme.spacing
    effective_fill = fill or palette.panel_fill
    effective_border = border or palette.panel_border
    effective_radius = spacing.panel_radius if radius is None else radius

    if alpha is None:
        pygame.draw.rect(surface, effective_fill, rect, border_radius=effective_radius)
    else:
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        fill_with_alpha = pygame.Color(effective_fill)
        fill_with_alpha.a = alpha
        pygame.draw.rect(
            overlay, fill_with_alpha, overlay.get_rect(), border_radius=effective_radius
        )
        surface.blit(overlay, rect)

    if border_width > 0:
        pygame.draw.rect(
            surface, effective_border, rect, width=border_width, border_radius=effective_radius
        )


def draw_overlay_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    radius: int | None = None,
    alpha: int | None = None,
    theme: GuiTheme = DEFAULT_THEME,
) -> None:
    palette = theme.palette
    spacing = theme.spacing
    draw_panel(
        surface,
        rect,
        radius=spacing.overlay_radius if radius is None else radius,
        fill=palette.overlay_fill,
        border=palette.panel_border_soft,
        alpha=palette.overlay_fill.a if alpha is None else alpha,
        theme=theme,
    )


def draw_button(
    surface: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    label: str,
    *,
    variant: ButtonVariant = "primary",
    hovered: bool = False,
    disabled: bool = False,
    theme: GuiTheme = DEFAULT_THEME,
) -> None:
    palette = theme.palette
    spacing = theme.spacing
    fill = _button_fill(variant, hovered=hovered, disabled=disabled, theme=theme)
    border = (
        palette.panel_border_active if hovered and not disabled else pygame.Color(210, 225, 245)
    )
    text_color = palette.text_muted if disabled else palette.text_primary

    pygame.draw.rect(surface, fill, rect, border_radius=spacing.button_radius)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=spacing.button_radius)
    drawer.draw_text(
        surface,
        label,
        centered_text_position(drawer, label, rect, role="small"),
        role="small",
        color=text_color,
    )


def draw_badge(
    surface: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    text: str,
    *,
    active: bool = False,
    fill: pygame.Color | None = None,
    border: pygame.Color | None = None,
    text_color: pygame.Color | None = None,
    theme: GuiTheme = DEFAULT_THEME,
) -> None:
    palette = theme.palette
    spacing = theme.spacing
    effective_fill = fill or (palette.accent if active else palette.panel_fill_soft)
    effective_border = border or (palette.panel_border_active if active else palette.panel_border)
    effective_text = text_color or palette.text_primary

    pygame.draw.rect(surface, effective_fill, rect, border_radius=spacing.badge_radius)
    pygame.draw.rect(surface, effective_border, rect, width=1, border_radius=spacing.badge_radius)
    drawer.draw_text(
        surface,
        text,
        centered_text_position(drawer, text, rect, role="tiny"),
        role="tiny",
        color=effective_text,
    )


def centered_text_position(
    drawer: PrimitiveDrawer,
    text: str,
    rect: pygame.Rect,
    *,
    role: str,
) -> tuple[int, int]:
    width, height = drawer.text_size(text, role=role)
    return (rect.centerx - width // 2, rect.centery - height // 2)


def _button_fill(
    variant: ButtonVariant,
    *,
    hovered: bool,
    disabled: bool,
    theme: GuiTheme,
) -> pygame.Color:
    palette = theme.palette
    if disabled:
        return palette.button_disabled
    if variant == "success":
        return palette.button_success_hover if hovered else palette.button_success
    if variant == "danger":
        return palette.button_danger_hover if hovered else palette.button_danger
    if variant == "neutral":
        return palette.panel_fill_soft.lerp(palette.text_primary, 0.08 if hovered else 0.0)
    return palette.button_primary_hover if hovered else palette.button_primary
