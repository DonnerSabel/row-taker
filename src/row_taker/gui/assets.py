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
