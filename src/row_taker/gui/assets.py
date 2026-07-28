from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from io import BytesIO
from pathlib import Path

import pygame

_ASSET_PACKAGE = "row_taker.assets"
_CARD_DIRECTORY = "cards"


@dataclass(frozen=True, slots=True)
class GuiAssets:
    """Load GUI images from package resources or an explicit directory."""

    image_dir: Path | None = None

    @classmethod
    def from_directory(cls, image_dir: str | Path) -> GuiAssets:
        return cls(image_dir=Path(image_dir))

    def scaled_card_image(self, card_value: int, width: int, height: int) -> pygame.Surface | None:
        return _scaled_card_image(self.image_dir, card_value, width, height)

    def scaled_connect_background(self, width: int, height: int) -> pygame.Surface | None:
        return _scaled_connect_background(self.image_dir, width, height)


DEFAULT_GUI_ASSETS = GuiAssets()


@lru_cache(maxsize=256)
def _scaled_card_image(
    image_dir: Path | None,
    card_value: int,
    width: int,
    height: int,
) -> pygame.Surface | None:
    image = _load_card_image(image_dir, card_value)
    if image is None:
        return None
    return pygame.transform.smoothscale(image, (width, height))


@lru_cache(maxsize=128)
def _load_card_image(image_dir: Path | None, card_value: int) -> pygame.Surface | None:
    filename = f"karte_{card_value:03}.png"
    image_data = _read_asset_bytes(
        image_dir,
        external_relative_path=Path(filename),
        packaged_relative_path=Path(_CARD_DIRECTORY) / filename,
    )
    if image_data is None:
        return None
    return pygame.image.load(BytesIO(image_data), filename).convert_alpha()


@lru_cache(maxsize=16)
def _scaled_connect_background(
    image_dir: Path | None,
    width: int,
    height: int,
) -> pygame.Surface | None:
    image = _load_connect_background(image_dir)
    if image is None:
        return None
    return _scale_cover(image, width, height)


@lru_cache(maxsize=8)
def _load_connect_background(image_dir: Path | None) -> pygame.Surface | None:
    filename = "connect_bg.png"
    image_data = _read_asset_bytes(
        image_dir,
        external_relative_path=Path(filename),
        packaged_relative_path=Path(filename),
    )
    if image_data is None:
        return None
    return pygame.image.load(BytesIO(image_data), filename).convert()


def _read_asset_bytes(
    image_dir: Path | None,
    *,
    external_relative_path: Path,
    packaged_relative_path: Path,
) -> bytes | None:
    if image_dir is not None:
        image_path = image_dir / external_relative_path
        if not image_path.is_file():
            return None
        return image_path.read_bytes()

    resource = files(_ASSET_PACKAGE)
    for path_part in packaged_relative_path.parts:
        resource = resource.joinpath(path_part)
    if not resource.is_file():
        return None
    return resource.read_bytes()


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
