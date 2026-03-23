from pathlib import Path
import pygame
from row_taker.gui.constants import CARD_ASPECT_RATIO, CARD_SCALE


class Card:
    """Darstellbare 6-nimmt!-Karte für Pygame mit Hover, Alpha-Hitbox und self.rect."""

    HOVER_SCALE = 1.2  # Faktor für Vergrößerung beim Hover

    def __init__(self, number: int, window_width: int):
        self.number = number
        self.points = self.calculate_points()
        self.image_orig: pygame.Surface | None = None
        self.image: pygame.Surface | None = None
        self.hover_image: pygame.Surface | None = None
        self.mask: pygame.Mask | None = None

        # Rect für Position und Größe
        self.rect: pygame.Rect | None = None

        # Pfad zum Bild
        project_root = Path(__file__).resolve().parents[3]
        self.image_path = project_root / "images" / f"{number:03}.png"

        if self.image_path.exists():
            self.image_orig = pygame.image.load(str(self.image_path)).convert_alpha()
            self.scale(window_width)
            self.rect = pygame.Rect(0, 0, self.image.get_width(), self.image.get_height())

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
        """Skaliert das Bild basierend auf CARD_SCALE und erzeugt Hover-Version."""
        if self.image_orig is None:
            self.image = None
            self.hover_image = None
            self.mask = None
            self.rect = None
            return

        width = int(window_width * CARD_SCALE)
        height = int(width * CARD_ASPECT_RATIO)

        # Normale Karte
        self.image = pygame.transform.scale(self.image_orig, (width, height))
        self.mask = pygame.mask.from_surface(self.image)

        # Hover-Karte
        hover_width = int(width * Card.HOVER_SCALE)
        hover_height = int(height * Card.HOVER_SCALE)
        self.hover_image = pygame.transform.scale(self.image_orig, (hover_width, hover_height))

        # Rect aktualisieren, falls noch nicht gesetzt
        if self.rect is None:
            self.rect = pygame.Rect(0, 0, width, height)
        else:
            self.rect.size = (width, height)

    def is_mouse_over(self, mouse_pos: tuple[int, int]) -> bool:
        """Prüft, ob die Maus über der Karte ist (Fensterkoordinaten, Alpha-Hitbox)."""
        if self.rect is None or self.mask is None:
            return False

        local_x = mouse_pos[0] - self.rect.x
        local_y = mouse_pos[1] - self.rect.y

        if 0 <= local_x < self.rect.width and 0 <= local_y < self.rect.height:
            return self.mask.get_at((local_x, local_y))
        return False

    def draw(self, surface: pygame.Surface, mouse_pos: tuple[int, int] | None = None) -> None:
        """Zeichnet die Karte. Hover-Version bei Maus über Karte."""
        if self.image is None or self.rect is None:
            return

        if mouse_pos is not None and self.is_mouse_over(mouse_pos):
            hover_x = self.rect.x - (self.hover_image.get_width() - self.rect.width) // 2
            hover_y = self.rect.y - (self.hover_image.get_height() - self.rect.height) // 2
            surface.blit(self.hover_image, (hover_x, hover_y))
        else:
            surface.blit(self.image, self.rect.topleft)