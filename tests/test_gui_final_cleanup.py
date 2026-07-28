from __future__ import annotations

from dataclasses import replace
from inspect import signature
from pathlib import Path
from unittest.mock import Mock

import pytest

pygame = pytest.importorskip("pygame")

from row_taker.client.core_state import ClientMode
from row_taker.gui import card
from row_taker.gui.app import GuiApp
from row_taker.gui.card import GuiCard
from row_taker.gui.game_visual_builder import build_game_visual_state
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui.screens.lobby_frame import LobbyFrame
from row_taker.gui_workbench.scenarios import get_scenario


def _prepared_screen_for(state):
    app = GuiApp()
    app._screen = pygame.Surface((1280, 720))
    app._live_client = Mock()
    app._client_state = state
    return app._prepare_current_screen()


def test_card_module_has_no_refactor_compatibility_api() -> None:
    assert not hasattr(card, "CardSprite")
    assert not hasattr(GuiCard, "from_card")


def test_public_visual_builder_has_no_test_override() -> None:
    assert "public_state_override" not in signature(build_game_visual_state).parameters


def test_gui_app_selects_frames_with_client_mode_enum(monkeypatch) -> None:
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (0, 0))
    lobby_state = get_scenario("lobby-waiting").state
    game_state = get_scenario("choose-card").state
    ended_state = replace(
        game_state,
        core_state=replace(
            game_state.core_state,
            client_mode=ClientMode.ENDED,
        ),
    )

    assert isinstance(_prepared_screen_for(lobby_state), LobbyFrame)
    assert isinstance(_prepared_screen_for(game_state), GameFrame)
    assert isinstance(_prepared_screen_for(ended_state), GameFrame)


def test_gui_source_contains_no_removed_cleanup_names() -> None:
    root = Path("src/row_taker/gui")
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))

    assert "CardSprite" not in source
    assert "public_state_override" not in source
    assert ".client_mode.value" not in source


def test_game_layout_has_no_background_artwork_compatibility_geometry() -> None:
    layout_source = Path("src/row_taker/gui/board_layout.py").read_text(encoding="utf-8")
    assets_source = Path("src/row_taker/gui/assets.py").read_text(encoding="utf-8")
    debug_source = Path("src/row_taker/gui/debug_layout.py").read_text(encoding="utf-8")

    for removed_name in (
        "BoardRegionRatios",
        "OpponentSlotGeometry",
        "main_play_rect",
        "opponent_area_rect",
        "stats_rect",
        "opponent_slots",
        "overlay_rect",
        "staged_card_size",
    ):
        assert removed_name not in layout_source

    assert "scaled_board_image_full" not in assets_source
    assert "board.png" not in debug_source
