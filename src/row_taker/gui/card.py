from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from row_taker.gui.assets import DEFAULT_GUI_ASSETS, GuiAssets
from row_taker.gui_common.primitives import (
    ACCENT,
    CARD_FILL,
    CARD_SELECTED,
    PANEL_BORDER,
    TEXT_MUTED,
    PrimitiveDrawer,
)


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
    ) -> None:
        image = assets.scaled_card_image(self.card_value, self.rect.width, self.rect.height)
        if image is None:
            self._draw_fallback(surface, drawer=drawer)
            return

        surface.blit(image, self.rect)
        self._draw_highlight(surface)

    def _draw_fallback(self, surface: pygame.Surface, *, drawer: PrimitiveDrawer) -> None:
        fill = CARD_SELECTED if self.selected else CARD_FILL
        border = ACCENT if self.selected or self.hovered else PANEL_BORDER
        border_width = 2 if self.selected or self.hovered else 1

        pygame.draw.rect(surface, fill, self.rect, border_radius=6)
        pygame.draw.rect(surface, border, self.rect, border_width, border_radius=6)
        drawer.draw_text(surface, str(self.card_value), (self.rect.left + 8, self.rect.top + 6), role="body")
        if self.bullheads is not None:
            drawer.draw_text(
                surface,
                f"{self.bullheads} bh",
                (self.rect.left + 8, self.rect.top + 30),
                role="small",
                color=TEXT_MUTED,
            )

    def _draw_highlight(self, surface: pygame.Surface) -> None:
        if not self.selected and not self.hovered:
            return
        border_width = 2 if self.selected else 1
        pygame.draw.rect(surface, ACCENT, self.rect.inflate(4, 4), border_width, border_radius=6)


# Compatibility name for older imports while the GUI is being refactored.
CardSprite = GuiCard


def draw_card_back(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw a neutral face-down card placeholder."""

    back = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(back, pygame.Color(18, 28, 40, 130), back.get_rect(), border_radius=6)
    surface.blit(back, rect)
    pygame.draw.rect(surface, pygame.Color(255, 255, 255, 65), rect, 1, border_radius=6)
