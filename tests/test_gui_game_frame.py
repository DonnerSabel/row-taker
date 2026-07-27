from __future__ import annotations

from unittest.mock import Mock

import pytest

pytest.importorskip("pygame")

from row_taker.gui.game_interaction import GameScreenTargets
from row_taker.gui.screens import game_screen
from row_taker.gui.screens.game_screen import GameFrame
from row_taker.gui_common.layout import compute_layout


def test_game_frame_prepares_geometry_and_targets_once(monkeypatch) -> None:
    layout = compute_layout(1280, 720)
    state = object()
    geometry = object()
    targets = GameScreenTargets()
    compute_geometry = Mock(return_value=geometry)
    build_targets = Mock(return_value=targets)
    monkeypatch.setattr(game_screen, "_compute_geometry", compute_geometry)
    monkeypatch.setattr(game_screen, "build_game_screen_targets", build_targets)

    frame = GameFrame.from_layout(
        layout=layout,
        state=state,
        frame_count=17,
        presentation_frame_count=5,
        last_action_summary="test",
    )

    compute_geometry.assert_called_once_with(layout.window_rect, state)
    build_targets.assert_called_once_with(geometry, state)
    assert frame.geometry is geometry
    assert frame.targets is targets
    assert frame.build_targets(layout) is targets
    compute_geometry.assert_called_once()
    build_targets.assert_called_once()


def test_game_frame_render_uses_prepared_geometry(monkeypatch) -> None:
    layout = compute_layout(1280, 720)
    state = object()
    geometry = object()
    targets = GameScreenTargets()
    screen = object()
    drawer = object()
    render_game_screen = Mock()
    monkeypatch.setattr(game_screen, "render_game_screen", render_game_screen)
    frame = GameFrame(
        state=state,
        frame_count=17,
        presentation_frame_count=5,
        last_action_summary="test",
        geometry=geometry,
        targets=targets,
    )

    frame.render(
        screen,
        drawer=drawer,
        layout=layout,
        targets=targets,
    )

    render_game_screen.assert_called_once_with(
        screen,
        drawer=drawer,
        geometry=geometry,
        client_state=state,
        game_targets=targets,
        frame_count=17,
        presentation_frame_count=5,
        last_action_summary="test",
    )
