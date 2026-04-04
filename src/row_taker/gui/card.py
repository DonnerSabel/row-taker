from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

from row_taker.engine.cards import Card
from row_taker.gui.constants import CARD_ASPECT_RATIO, CARD_SCALE


@dataclass(slots=True)
class CardSprite:
    """Darstellbare 6-nimmt!-Karte mit Hover, Alpha-Hitbox und Auswahlrahmen."""

    card: Card
    image_path: Path | None = None
    x: float = 0.0
    y: float = 0.0
    scale_factor: float = 1.0
    is_face_up: bool = True
    selected: bool = False

    image_orig: pygame.Surface | None = None
    image: pygame.Surface | None = None
    hover_image: pygame.Surface | None = None
    mask: pygame.Mask | None = None
    rect: pygame.Rect | None = None

    HOVER_SCALE = 1.2

    def __post_init__(self) -> None:
        self.validate()

        if self.image_path is None:
            project_root = Path(__file__).resolve().parents[3]
            self.image_path = project_root / "images" / f"{self.value:03}.png"

        if self.image_path.exists():
            self.image_orig = pygame.image.load(str(self.image_path)).convert_alpha()

    def validate(self) -> None:
        self.card.validate()

        if self.scale_factor <= 0:
            raise ValueError(f"scale_factor must be > 0, got {self.scale_factor}")

    @property
    def value(self) -> int:
        return self.card.value

    @property
    def bullheads(self) -> int:
        return self.card.bullheads

    @property
    def points(self) -> int:
        return self.card.points

    def move_to(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

        if self.rect is not None:
            self.rect.topleft = (round(self.x), round(self.y))

    def set_scale(self, scale_factor: float) -> None:
        if scale_factor <= 0:
            raise ValueError(f"scale_factor must be > 0, got {scale_factor}")
        self.scale_factor = scale_factor

    def scale(self, window_width: int) -> None:
        """Skaliert die Karte basierend auf CARD_SCALE und erzeugt die Hover-Version."""
        if self.image_orig is None:
            return

        width = int(window_width * CARD_SCALE * self.scale_factor)
        height = int(width * CARD_ASPECT_RATIO)

        self.image = pygame.transform.scale(self.image_orig, (width, height))
        self.mask = pygame.mask.from_surface(self.image)

        hover_width = int(width * self.HOVER_SCALE)
        hover_height = int(height * self.HOVER_SCALE)
        self.hover_image = pygame.transform.scale(self.image_orig, (hover_width, hover_height))

        if self.rect is None:
            self.rect = pygame.Rect(round(self.x), round(self.y), width, height)
        else:
            self.rect.topleft = (round(self.x), round(self.y))
            self.rect.size = (width, height)

    def is_mouse_over(self, mouse_pos: tuple[int, int]) -> bool:
        """Prüft, ob die Maus über der Karte liegt, inklusive Alpha-Hitbox."""
        if self.rect is None or self.mask is None:
            return False

        local_x = mouse_pos[0] - self.rect.x
        local_y = mouse_pos[1] - self.rect.y

        if 0 <= local_x < self.rect.width and 0 <= local_y < self.rect.height:
            return bool(self.mask.get_at((local_x, local_y)))

        return False

    def draw(self, surface: pygame.Surface, mouse_pos: tuple[int, int] | None = None) -> None:
        """Zeichnet die Karte; bei Hover wird sie vergrößert dargestellt."""
        if self.image is None or self.rect is None:
            return

        self.rect.topleft = (round(self.x), round(self.y))

        if mouse_pos is not None and self.is_mouse_over(mouse_pos) and self.hover_image is not None:
            hover_x = self.rect.x - (self.hover_image.get_width() - self.rect.width) // 2
            hover_y = self.rect.y - (self.hover_image.get_height() - self.rect.height) // 2
            surface.blit(self.hover_image, (hover_x, hover_y))
        else:
            surface.blit(self.image, self.rect.topleft)

        if self.selected:
            pygame.draw.rect(surface, (255, 255, 0), self.rect, 3)
