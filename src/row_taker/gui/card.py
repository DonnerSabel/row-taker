# card.py
from pathlib import Path

import pygame

from row_taker.gui.constants import CARD_ASPECT_RATIO, CARD_SCALE


class Card:
    """Darstellbare 6-nimmt!-Karte mit Hover und Alpha-Hitbox."""

    HOVER_SCALE = 1.2  # Vergrößerungsfaktor bei Hover

    def __init__(self, number: int):
        self.number = number
        self.points = self.calculate_points()

        self.image_orig: pygame.Surface | None = None
        self.image: pygame.Surface | None = None
        self.hover_image: pygame.Surface | None = None
        self.mask: pygame.Mask | None = None
        self.rect: pygame.Rect | None = None
        self.x = 0
        self.y = 0
        self.selected = False  # New: selection state

        # Pfad zum Bild
        project_root = Path(__file__).resolve().parents[3]
        self.image_path = project_root / "images" / f"{number:03}.png"
        if self.image_path.exists():
            self.image_orig = pygame.image.load(str(self.image_path)).convert_alpha()

    def calculate_points(self) -> int:
        """Berechnet die Hornochsen-Punkte nach Spielregeln"""
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
        """Skaliert die Karte basierend auf CARD_SCALE und erzeugt Hover-Version"""
        if self.image_orig is None:
            return

        width = int(window_width * CARD_SCALE)
        height = int(width * CARD_ASPECT_RATIO)

        self.image = pygame.transform.scale(self.image_orig, (width, height))
        self.mask = pygame.mask.from_surface(self.image)

        # Hover-Version
        hover_width = int(width * self.HOVER_SCALE)
        hover_height = int(height * self.HOVER_SCALE)
        self.hover_image = pygame.transform.scale(self.image_orig, (hover_width, hover_height))

        if self.rect is None:
            self.rect = pygame.Rect(self.x, self.y, width, height)
        else:
            self.rect.size = (width, height)

    def is_mouse_over(self, mouse_pos: tuple[int, int]) -> bool:
        """Prüft, ob Maus über Karte (inkl. Alpha-Hitbox)"""
        if self.rect is None or self.mask is None:
            return False

        local_x = mouse_pos[0] - self.rect.x
        local_y = mouse_pos[1] - self.rect.y
        if 0 <= local_x < self.rect.width and 0 <= local_y < self.rect.height:
            return bool(self.mask.get_at((local_x, local_y)))
        return False

    def draw(self, surface: pygame.Surface, mouse_pos: tuple[int, int] | None = None) -> None:
        """Zeichnet Karte; vergrößert bei Maus-Hover"""
        if self.image is None or self.rect is None:
            return

        self.rect.topleft = (self.x, self.y)

        if mouse_pos and self.is_mouse_over(mouse_pos) and self.hover_image is not None:
            hover_x = self.rect.x - (self.hover_image.get_width() - self.rect.width) // 2
            hover_y = self.rect.y - (self.hover_image.get_height() - self.rect.height) // 2
            surface.blit(self.hover_image, (hover_x, hover_y))
        else:
            surface.blit(self.image, self.rect.topleft)

        # Draw selection border
        if self.selected:
            pygame.draw.rect(surface, (255, 255, 0), self.rect, 3)  # Yellow border for selected
