from __future__ import annotations

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.rendering.game_hud_renderer import (
    _fit_text_to_width,
    player_staged_card_rects,
)
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui_workbench.app import prepare_headless_pygame, prepare_scenario_frame
from row_taker.gui_workbench.scenarios import get_scenario


@pytest.fixture(scope="module", autouse=True)
def initialized_pygame() -> None:
    prepare_headless_pygame()
    yield
    pygame.quit()


def test_staged_card_mapping_uses_every_players_tile() -> None:
    frame = prepare_scenario_frame(get_scenario("cards-revealed"))
    assert isinstance(frame, GameFrame)

    mapping = player_staged_card_rects(frame.visual_state, frame.geometry)

    expected = {
        player.player_id: tile.card_placement.rect
        for player, tile in zip(
            frame.visual_state.opponents,
            frame.geometry.opponent_tiles,
            strict=False,
        )
    }
    own_player = frame.visual_state.own_player
    assert own_player is not None
    expected[own_player.player_id] = (
        frame.geometry.own_player_tile.card_placement.rect
    )
    assert mapping == expected


def test_long_player_name_is_shortened_to_available_pixel_width() -> None:
    drawer = PrimitiveDrawer()
    original = "Benedikt-von-der-Testspielrunde"

    shortened = _fit_text_to_width(
        drawer,
        original,
        max_width=120,
        role="small",
    )

    assert shortened.endswith("…")
    assert shortened != original
    assert drawer._font_for_role("small").size(shortened)[0] <= 120


def test_short_player_name_is_not_changed() -> None:
    drawer = PrimitiveDrawer()

    assert (
        _fit_text_to_width(
            drawer,
            "Ben",
            max_width=120,
            role="small",
        )
        == "Ben"
    )


def test_revealed_own_card_moves_from_hand_to_own_tile() -> None:
    frame = prepare_scenario_frame(get_scenario("cards-revealed"))
    assert isinstance(frame, GameFrame)
    own_player = frame.visual_state.own_player

    assert own_player is not None
    assert own_player.staged_card_value is not None
    own_hand_card = next(
        card
        for card in frame.visual_state.hand
        if card.card_value == own_player.staged_card_value
    )
    assert own_hand_card.visible is False
    assert frame.geometry.own_player_rect.contains(
        frame.geometry.own_player_tile.card_placement.rect
    )
