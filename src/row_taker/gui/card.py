from pathlib import Path

import pygame

from row_taker.gui.constants import CARD_ASPECT_RATIO, CARD_SCALE


class Card:
    """Eine darstellbare 6-nimmt!-Karte für Pygame."""

    def __init__(self, number: int):
        self.number = number
        self.points = self.calculate_points()
        self.x = 0
        self.y = 0
        self.image_orig: pygame.Surface | None = None
        self.image: pygame.Surface | None = None

        project_root = Path(__file__).resolve().parents[3]
        self.image_path = project_root / "images" / f"{number:03}.png"

        if self.image_path.exists():
            self.image_orig = pygame.image.load(str(self.image_path)).convert_alpha()

    def calculate_points(self) -> int:
        n = self.number
        if n == 55:
            return 7
        if n % 11 == 0:
            return 5
        if n % 10 == 0:
            return 3
        if n % 5 == 0:
            return 2
        return 1

    def scale(self, window_width: int) -> None:
        if self.image_orig is None:
            self.image = None
            return

        width = int(window_width * CARD_SCALE)
        height = int(width * CARD_ASPECT_RATIO)
        self.image = pygame.transform.scale(self.image_orig, (width, height))

    def draw(self, surface: pygame.Surface) -> None:
        if self.image is not None:
            surface.blit(self.image, (self.x, self.y))
