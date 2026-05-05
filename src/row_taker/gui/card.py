from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from row_taker.gui.assets import DEFAULT_GUI_ASSETS, GuiAssets
from row_taker.gui.theme import DEFAULT_THEME, GuiTheme
from row_taker.gui_common.primitives import PrimitiveDrawer


@dataclass(frozen=True, slots=True)
class GuiCard:
    """Presentation-only card object for hit testing and drawing.

    The engine owns card rules and state. ``GuiCard`` only knows where a card is
    on screen and how that card should currently look.
    """

    card_value: int
    bullheads: int | None
    rect: pygame.Rect
    selected: bool = False
    hovered: bool = False

    @classmethod
    def from_card(
        cls,
        card: Any,
        rect: pygame.Rect,
        *,
        selected: bool = False,
        hovered: bool = False,
    ) -> GuiCard:
        return cls(
            card_value=int(card.value),
            bullheads=int(card.bullheads),
            rect=rect,
            selected=selected,
            hovered=hovered,
        )

    @classmethod
    def from_card_value(
        cls,
        card_value: int,
        rect: pygame.Rect,
        *,
        selected: bool = False,
        hovered: bool = False,
    ) -> GuiCard:
        return cls(
            card_value=card_value,
            bullheads=None,
            rect=rect,
            selected=selected,
            hovered=hovered,
        )

    @property
    def value(self) -> int:
        return self.card_value

    def contains_point(self, position: tuple[int, int]) -> bool:
        return self.rect.collidepoint(position)

    def draw(
        self,
        surface: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
        assets: GuiAssets = DEFAULT_GUI_ASSETS,
        theme: GuiTheme = DEFAULT_THEME,
    ) -> None:
        image = assets.scaled_card_image(self.card_value, self.rect.width, self.rect.height)
        if image is None:
            self._draw_fallback(surface, drawer=drawer, theme=theme)
            return

        surface.blit(image, self.rect)
        self._draw_highlight(surface, theme=theme)

    def _draw_fallback(
        self,
        surface: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
        theme: GuiTheme,
    ) -> None:
        palette = theme.palette
        spacing = theme.spacing
        fill = palette.card_selected if self.selected else palette.card_fill
        border = _card_border_color(selected=self.selected, hovered=self.hovered, theme=theme)
        border_width = 2 if self.selected or self.hovered else 1

        pygame.draw.rect(surface, fill, self.rect, border_radius=spacing.card_radius)
        pygame.draw.rect(surface, border, self.rect, border_width, border_radius=spacing.card_radius)
        drawer.draw_text(surface, str(self.card_value), (self.rect.left + 8, self.rect.top + 6), role="body")
        if self.bullheads is not None:
            drawer.draw_text(
                surface,
                f"{self.bullheads} bh",
                (self.rect.left + 8, self.rect.top + 30),
                role="small",
                color=palette.text_muted,
            )

    def _draw_highlight(self, surface: pygame.Surface, *, theme: GuiTheme) -> None:
        if not self.selected and not self.hovered:
            return
        border_width = 3 if self.selected else 2
        pygame.draw.rect(
            surface,
            _card_border_color(selected=self.selected, hovered=self.hovered, theme=theme),
            self.rect.inflate(4, 4),
            border_width,
            border_radius=theme.spacing.card_radius,
        )



def _card_border_color(*, selected: bool, hovered: bool, theme: GuiTheme) -> pygame.Color:
    if selected:
        return theme.palette.accent
    if hovered:
        return theme.palette.accent_hover
    return theme.palette.panel_border


# Compatibility name for older imports while the GUI is being refactored.
CardSprite = GuiCard


def draw_card_back(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    theme: GuiTheme = DEFAULT_THEME,
) -> None:
    """Draw a neutral face-down card placeholder."""

    palette = theme.palette
    spacing = theme.spacing
    back = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(back, palette.card_back_fill, back.get_rect(), border_radius=spacing.card_radius)
    surface.blit(back, rect)
    pygame.draw.rect(surface, palette.card_back_border, rect, 1, border_radius=spacing.card_radius)
