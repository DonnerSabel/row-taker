from pathlib import Path
from typing import cast

import pygame

from row_taker.gui.constants import CARD_ASPECT_RATIO, CARD_SCALE


class Card:
    HOVER_SCALE: float = 1.2

    def __init__(self, number: int) -> None:
        self.number: int = number
        self.points: int = self.calculate_points()
        self.image_orig: pygame.Surface | None = None
        self.image: pygame.Surface | None = None
        self.hover_image: pygame.Surface | None = None
        self.mask: pygame.mask.Mask | None = None
        self.x, self.y = 0.0, 0.0
        self.target_x, self.target_y = 0.0, 0.0
        self.base_width, self.base_height = 0, 0
        self.current_scale: float = 1.0
        self.phase: str = "HAND"
        self.visible: bool = True
        self.selected: bool = False

        project_root: Path = Path(__file__).resolve().parents[3]
        self.image_path: Path = project_root / "images" / f"karte_{number:03}.png"
        if self.image_path.exists():
            img = pygame.image.load(str(self.image_path)).convert_alpha()
            self.image_orig = cast(pygame.Surface, img)
        self.rect: pygame.Rect = pygame.Rect(0, 0, 0, 0)

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
            return
        self.base_width = int(window_width * CARD_SCALE)
        self.base_height = int(self.base_width * CARD_ASPECT_RATIO)
        self.set_scale_factor(1.0)

    def set_scale_factor(self, factor: float) -> None:
        if self.image_orig is None:
            return
        self.current_scale = factor
        w, h = max(1, int(self.base_width * factor)), max(1, int(self.base_height * factor))
        self.image = cast(pygame.Surface, pygame.transform.smoothscale(self.image_orig, (w, h)))
        if factor == 1.0:
            self.mask = pygame.mask.from_surface(self.image)
            self.hover_image = cast(
                pygame.Surface,
                pygame.transform.smoothscale(
                    self.image_orig, (int(w * self.HOVER_SCALE), int(h * self.HOVER_SCALE))
                ),
            )
        self.rect.width, self.rect.height = w, h

    def is_at_target(self) -> bool:
        return abs(self.x - self.target_x) < 15 and abs(self.y - self.target_y) < 15

    def is_mouse_over(self, mouse_pos: tuple[int, int]) -> bool:
        if not self.visible or self.mask is None:
            return False
        lx, ly = mouse_pos[0] - int(self.x), mouse_pos[1] - int(self.y)
        if 0 <= lx < self.rect.width and 0 <= ly < self.rect.height:
            try:
                return bool(self.mask.get_at((lx, ly)))
            except (IndexError, ValueError):
                return False
        return False

    def spawn_from(self, start_x: float, start_y: float) -> None:
        self.x, self.y = start_x, start_y
        self.set_scale_factor(0.1)

    def fly_off_screen(self) -> None:
        self.target_x = -500.0
        self.phase = "DISCARDING"

    def update(self) -> None:
        if not self.visible:
            return
        if self.current_scale < 1.0:
            self.set_scale_factor(min(1.0, self.current_scale + 0.03))
        self.x += (self.target_x - self.x) * 0.05
        self.y += (self.target_y - self.y) * 0.05
        if self.phase == "DISCARDING" and abs(self.target_x - self.x) < 20:
            self.visible = False
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self, surface: pygame.Surface, mouse_pos: tuple[int, int] | None = None) -> None:
        if not self.visible or self.image is None:
            return
        img = self.image
        is_hovered = (
            mouse_pos is not None and self.current_scale == 1.0 and self.is_mouse_over(mouse_pos)
        )
        dx, dy = int(self.x), int(self.y)
        if is_hovered and self.hover_image is not None:
            img = self.hover_image
            dx -= (img.get_width() - self.base_width) // 2
            dy -= (img.get_height() - self.base_height) // 2
        surface.blit(img, (dx, dy))
        if self.selected:
            pygame.draw.rect(surface, (255, 255, 0), (dx, dy, img.get_width(), img.get_height()), 3)
