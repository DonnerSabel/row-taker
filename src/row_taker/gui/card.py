from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

from row_taker.engine.game.cards import Card


@dataclass(slots=True)
class CardSprite:
    """Visual representation of a game card.

    This class is intentionally presentation-only. It does not own game logic and
    does not mutate engine state.
    """

    card: Card
    image: pygame.Surface | None = None
    rect: pygame.Rect | None = None
    selected: bool = False
    hovered: bool = False

    @classmethod
    def from_card(cls, card: Card) -> CardSprite:
        sprite = cls(card=card)
        sprite.load_image()
        return sprite

    @property
    def value(self) -> int:
        return self.card.value

    def load_image(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        image_path = project_root / "images" / f"karte_{self.card.value:03}.png"
        if not image_path.exists():
            self.image = None
            self.rect = None
            return

        self.image = pygame.image.load(str(image_path)).convert_alpha()
        self.rect = self.image.get_rect()

    def scale_to_width(self, width: int) -> None:
        if self.image is None:
            return

        current_width, current_height = self.image.get_size()
        if current_width <= 0:
            return

        height = max(1, round(current_height * width / current_width))
        self.image = pygame.transform.smoothscale(self.image, (width, height))
        old_topleft = self.rect.topleft if self.rect is not None else (0, 0)
        self.rect = self.image.get_rect(topleft=old_topleft)

    def move_to(self, x: int, y: int) -> None:
        if self.rect is None:
            self.rect = pygame.Rect(x, y, 0, 0)
            return
        self.rect.topleft = (x, y)

    def contains(self, position: tuple[int, int]) -> bool:
        return self.rect is not None and self.rect.collidepoint(position)

    def draw(self, surface: pygame.Surface) -> None:
        if self.image is None or self.rect is None:
            return
        surface.blit(self.image, self.rect)
