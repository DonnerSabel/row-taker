from __future__ import annotations

import os
from importlib.resources import files
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from row_taker.gui.assets import DEFAULT_GUI_ASSETS, GuiAssets


@pytest.fixture(scope="module", autouse=True)
def initialized_pygame_display() -> None:
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))


def test_packaged_resources_contain_cards_and_backgrounds() -> None:
    asset_root = files("row_taker.assets")

    assert asset_root.joinpath("cards", "karte_001.png").is_file()
    assert asset_root.joinpath("cards", "karte_104.png").is_file()
    assert asset_root.joinpath("connect_bg.png").is_file()
    assert asset_root.joinpath("board.png").is_file()
    assert asset_root.joinpath("titel.png").is_file()


def test_default_assets_load_and_scale_packaged_card() -> None:
    image = DEFAULT_GUI_ASSETS.scaled_card_image(1, 72, 108)

    assert image is not None
    assert image.get_size() == (72, 108)


def test_default_assets_load_and_scale_packaged_connect_background() -> None:
    image = DEFAULT_GUI_ASSETS.scaled_connect_background(320, 180)

    assert image is not None
    assert image.get_size() == (320, 180)


def test_missing_packaged_card_returns_none() -> None:
    assert DEFAULT_GUI_ASSETS.scaled_card_image(999, 72, 108) is None


def test_explicit_external_image_directory_remains_supported(tmp_path: Path) -> None:
    card_source = files("row_taker.assets").joinpath("cards", "karte_007.png")
    background_source = files("row_taker.assets").joinpath("connect_bg.png")
    (tmp_path / "karte_007.png").write_bytes(card_source.read_bytes())
    (tmp_path / "connect_bg.png").write_bytes(background_source.read_bytes())
    assets = GuiAssets.from_directory(tmp_path)

    card = assets.scaled_card_image(7, 64, 96)
    background = assets.scaled_connect_background(200, 120)

    assert card is not None
    assert card.get_size() == (64, 96)
    assert background is not None
    assert background.get_size() == (200, 120)
    assert assets.scaled_card_image(8, 64, 96) is None
