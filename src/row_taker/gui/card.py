from pathlib import Path
import time
import pygame
from row_taker.gui.constants import CARD_SCALE, CARD_ASPECT_RATIO


class Card:
    HOVER_SCALE = 1.2

    def __init__(self, number: int):
        self.number = number
        self.points = self.calculate_points()

        # Bilder
        self.image_orig: pygame.Surface | None = None
        self.image: pygame.Surface | None = None
        self.hover_image: pygame.Surface | None = None
        self.mask: pygame.Mask | None = None

        # Position (Zentrum)
        self.x = 0.0
        self.y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.rect: pygame.Rect | None = None

        # Zustand & Phasen
        self.phase = "HAND"
        self.played = False
        self.selection_time = 0.0

        # Basis-Höhen (Y-Koordinaten für das Zentrum)
        self.y_hidden = 0
        self.y_revealed = 0

        # Bild laden
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

    def scale(self, window_width: int, window_height: int) -> None:
        if self.image_orig is None:
            return

        width = int(window_width * CARD_SCALE)
        height = int(width * CARD_ASPECT_RATIO)

        self.image = pygame.transform.scale(self.image_orig, (width, height))
        self.mask = pygame.mask.from_surface(self.image)

        hover_w = int(width * self.HOVER_SCALE)
        hover_h = int(height * self.HOVER_SCALE)
        self.hover_image = pygame.transform.scale(self.image_orig, (hover_w, hover_h))

        # Y-Zentren berechnen (1/4 sichtbar am unteren Rand)
        self.y_hidden = window_height - (height // 4) + (height // 2)
        self.y_revealed = window_height - (height // 2) - 10

        if self.rect is None:
            self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))
        else:
            self.rect.size = (width, height)

    def is_mouse_over(self, mouse_pos):
        if self.rect is None or self.mask is None:
            return False

        lx = mouse_pos[0] - self.rect.x
        ly = mouse_pos[1] - self.rect.y

        if 0 <= lx < self.rect.width and 0 <= ly < self.rect.height:
            try:
                return self.mask.get_at((lx, ly))
            except IndexError:
                return False
        return False

    def update(self):
        if self.phase == "WAITING":
            if time.time() - self.selection_time >= 10:
                self.phase = "FLYING"
                self.target_x = 50 + (self.rect.width // 2 if self.rect else 0)
                self.target_y = 50 + (self.rect.height // 2 if self.rect else 0)

        # Weiche Bewegung
        self.x += (self.target_x - self.x) * 0.1
        self.y += (self.target_y - self.y) * 0.1

        if self.phase == "FLYING":
            if abs(self.target_x - self.x) < 2 and abs(self.target_y - self.y) < 2:
                self.phase = "PLAYED"
                self.x = self.target_x
                self.y = self.target_y

        if self.rect:
            self.rect.center = (int(self.x), int(self.y))

    # 🔥 NEU: allow_hand_hover steuert, ob die Karte in der Hand vergrößert werden darf
    def draw(self, surface: pygame.Surface, mouse_pos=None, allow_hand_hover=True):
        if self.image is None or self.rect is None:
            return

        is_hovered = mouse_pos and self.is_mouse_over(mouse_pos)
        img = self.image

        if is_hovered:
            if self.phase == "PLAYED":
                img = self.hover_image  # Gespielte Karten dürfen immer vergrößern
            elif self.phase == "HAND" and allow_hand_hover:
                img = self.hover_image  # Hand-Karten nur, wenn die Auswahl aktiv ist

        draw_rect = img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(img, draw_rect.topleft)
