from pathlib import Path

import pygame


class Spielfeld:
    """Hintergrundbild des Spielfelds."""

    def __init__(self, image_name: str = "board"):
        project_root = Path(__file__).resolve().parents[3]
        self.image_path = project_root / "images" / f"{image_name}.png"
        self.image: pygame.Surface | None = None
        self.rect: pygame.Rect | None = None

    def load_image(self) -> None:
        try:
            self.image = pygame.image.load(str(self.image_path))
            self.rect = self.image.get_rect(topleft=(0, 0))
        except FileNotFoundError:
            print(f"Fehler: Bild nicht gefunden: {self.image_path}")
            self.image = None
            self.rect = None

    def get_image_size(self) -> tuple[int, int]:
        if self.image is not None:
            return self.image.get_size()
        return (800, 600)

    def draw(self, screen: pygame.Surface) -> None:
        if self.image is not None and self.rect is not None:
            screen.blit(self.image, self.rect)
