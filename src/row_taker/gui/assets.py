from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pygame


def default_image_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "images"


@dataclass(frozen=True, slots=True)
class GuiAssets:
    image_dir: Path

    def scaled_board_image_full(self, width: int, height: int) -> pygame.Surface | None:
        return _scaled_board_image_full(self.image_dir, width, height)

    def scaled_card_image(self, card_value: int, width: int, height: int) -> pygame.Surface | None:
        return _scaled_card_image(self.image_dir, card_value, width, height)

    def scaled_connect_background(self, width: int, height: int) -> pygame.Surface | None:
        return _scaled_connect_background(self.image_dir, width, height)


DEFAULT_GUI_ASSETS = GuiAssets(image_dir=default_image_dir())


@lru_cache(maxsize=64)
def _scaled_board_image_full(image_dir: Path, width: int, height: int) -> pygame.Surface | None:
    image = _load_board_image(image_dir)
    if image is None:
        return None
    return pygame.transform.smoothscale(image, (width, height))


@lru_cache(maxsize=8)
def _load_board_image(image_dir: Path) -> pygame.Surface | None:
    image_path = image_dir / "board.png"
    if not image_path.exists():
        return None
    return pygame.image.load(str(image_path)).convert_alpha()


@lru_cache(maxsize=256)
def _scaled_card_image(image_dir: Path, card_value: int, width: int, height: int) -> pygame.Surface | None:
    image = _load_card_image(image_dir, card_value)
    if image is None:
        return None
    return pygame.transform.smoothscale(image, (width, height))


@lru_cache(maxsize=128)
def _load_card_image(image_dir: Path, card_value: int) -> pygame.Surface | None:
    image_path = image_dir / f"karte_{card_value:03}.png"
    if not image_path.exists():
        return None
    return pygame.image.load(str(image_path)).convert_alpha()


@lru_cache(maxsize=16)
def _scaled_connect_background(image_dir: Path, width: int, height: int) -> pygame.Surface | None:
    image = _load_connect_background(image_dir)
    if image is None:
        return None
    return _scale_cover(image, width, height)


@lru_cache(maxsize=8)
def _load_connect_background(image_dir: Path) -> pygame.Surface | None:
    image_path = image_dir / "connect_bg.png"
    if not image_path.exists():
        return None
    return pygame.image.load(str(image_path)).convert()


def _scale_cover(image: pygame.Surface, width: int, height: int) -> pygame.Surface:
    source_width, source_height = image.get_size()
    if source_width <= 0 or source_height <= 0:
        return pygame.Surface((width, height))

    scale = max(width / source_width, height / source_height)
    scaled_width = max(1, int(round(source_width * scale)))
    scaled_height = max(1, int(round(source_height * scale)))
    scaled = pygame.transform.smoothscale(image, (scaled_width, scaled_height))

    x = (scaled_width - width) // 2
    y = (scaled_height - height) // 2
    return scaled.subsurface((x, y, width, height)).copy()
