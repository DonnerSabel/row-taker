from __future__ import annotations

from unittest.mock import Mock

import pytest

pytest.importorskip("pygame")

from row_taker.gui import game_interaction
from row_taker.gui.game_interaction import GameScreenTargets, build_game_screen_targets
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui_workbench.app import OFFSCREEN_MOUSE_POS, prepare_scenario_frame
from row_taker.gui_workbench.scenarios import get_scenario


def _replace_target_builders(monkeypatch, *, card_targets, row_targets, continue_target) -> tuple[Mock, Mock, Mock]:
    card_builder = Mock(return_value=card_targets)
    row_builder = Mock(return_value=row_targets)
    continue_builder = Mock(return_value=continue_target)
    monkeypatch.setattr(game_interaction, "_build_card_targets", card_builder)
    monkeypatch.setattr(game_interaction, "_build_row_targets", row_builder)
    monkeypatch.setattr(game_interaction, "_build_continue_target", continue_builder)
    return card_builder, row_builder, continue_builder


def test_build_game_screen_targets_uses_live_mouse_by_default(monkeypatch) -> None:
    geometry = object()
    state = object()
    mouse_pos = (21, 34)
    get_pos = Mock(return_value=mouse_pos)
    monkeypatch.setattr(game_interaction.pygame.mouse, "get_pos", get_pos)
    card_builder, row_builder, continue_builder = _replace_target_builders(
        monkeypatch,
        card_targets=("card",),
        row_targets=("row",),
        continue_target="continue",
    )

    result = build_game_screen_targets(geometry, state)

    assert result == GameScreenTargets(
        card_targets=("card",),
        row_targets=("row",),
        continue_target="continue",
    )
    get_pos.assert_called_once_with()
    card_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)
    row_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)
    continue_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)


def test_build_game_screen_targets_uses_explicit_mouse_without_reading_pygame(monkeypatch) -> None:
    geometry = object()
    state = object()
    mouse_pos = (-1, -1)
    get_pos = Mock(side_effect=AssertionError("pygame mouse must not be read"))
    monkeypatch.setattr(game_interaction.pygame.mouse, "get_pos", get_pos)
    card_builder, row_builder, continue_builder = _replace_target_builders(
        monkeypatch,
        card_targets=(),
        row_targets=(),
        continue_target=None,
    )

    result = build_game_screen_targets(
        geometry,
        state,
        mouse_pos=mouse_pos,
    )

    assert result == GameScreenTargets()
    get_pos.assert_not_called()
    card_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)
    row_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)
    continue_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)

def test_continue_target_stays_inside_new_presentation_region() -> None:
    frame = prepare_scenario_frame(
        get_scenario("cards-revealed"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    assert isinstance(frame, GameFrame)
    assert frame.targets.continue_target is not None
    assert frame.geometry.presentation_rect.contains(
        frame.targets.continue_target.rect
    )

