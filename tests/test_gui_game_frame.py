from __future__ import annotations

from unittest.mock import Mock

import pytest

pytest.importorskip("pygame")

from row_taker.gui.game_interaction import GameScreenTargets
from row_taker.gui.screens import game_screen
from row_taker.gui.screens.game_screen import GameFrame
from row_taker.gui_common.layout import compute_layout
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT


def _frame(
    *,
    visual_state: object | None = None,
    geometry: object | None = None,
    targets: GameScreenTargets | None = None,
) -> GameFrame:
    return GameFrame(
        visual_state=object() if visual_state is None else visual_state,
        frame_count=17,
        presentation_frame_count=5,
        geometry=object() if geometry is None else geometry,
        targets=GameScreenTargets() if targets is None else targets,
    )


def test_game_frame_prepares_visual_state_geometry_and_targets_once(monkeypatch) -> None:
    layout = compute_layout(1280, 720)
    state = object()
    visual_state = object()
    geometry = Mock(window_rect=layout.window_rect)
    targets = GameScreenTargets()
    build_visual_state = Mock(return_value=visual_state)
    compute_geometry = Mock(return_value=geometry)
    build_targets = Mock(return_value=targets)
    monkeypatch.setattr(game_screen, "build_game_visual_state", build_visual_state)
    monkeypatch.setattr(game_screen, "_compute_geometry", compute_geometry)
    monkeypatch.setattr(game_screen, "build_game_screen_targets", build_targets)

    frame = GameFrame.from_layout(
        layout=layout,
        state=state,
        frame_count=17,
        presentation_frame_count=5,
        last_action_summary="test",
        mouse_pos=(123, 456),
    )

    build_visual_state.assert_called_once_with(
        state,
        last_action_summary="test",
        presentation_frame_count=5,
    )
    compute_geometry.assert_called_once_with(layout.window_rect, visual_state)
    build_targets.assert_called_once_with(
        geometry,
        visual_state,
        mouse_pos=(123, 456),
    )
    assert frame.visual_state is visual_state
    assert frame.geometry is geometry
    assert frame.targets is targets
    assert frame.build_targets(layout) is targets


def test_game_frame_render_uses_its_prepared_visual_state_and_targets(monkeypatch) -> None:
    visual_state = object()
    geometry = object()
    targets = GameScreenTargets()
    screen = object()
    drawer = object()
    render_game_screen = Mock()
    monkeypatch.setattr(game_screen, "render_game_screen", render_game_screen)
    frame = _frame(
        visual_state=visual_state,
        geometry=geometry,
        targets=targets,
    )

    frame.render(screen, drawer=drawer)

    render_game_screen.assert_called_once_with(
        screen,
        drawer=drawer,
        geometry=geometry,
        visual_state=visual_state,
        game_targets=targets,
        frame_count=17,
        presentation_frame_count=5,
    )


def test_game_frame_handle_event_uses_its_visual_state_and_targets(monkeypatch) -> None:
    visual_state = object()
    targets = GameScreenTargets()
    event = object()
    handle_game_event = Mock(return_value=NO_SCREEN_RESULT)
    monkeypatch.setattr(game_screen, "handle_game_event", handle_game_event)
    frame = _frame(visual_state=visual_state, targets=targets)

    assert frame.handle_event(event) is NO_SCREEN_RESULT
    handle_game_event.assert_called_once_with(
        event,
        visual_state=visual_state,
        game_targets=targets,
    )


def test_game_frame_rejects_layout_from_another_window() -> None:
    layout = compute_layout(1280, 720)
    other_layout = compute_layout(1400, 800)
    geometry = Mock(window_rect=layout.window_rect)
    frame = _frame(geometry=geometry)

    with pytest.raises(ValueError, match="different window layout"):
        frame.build_targets(other_layout)


def test_game_frame_rejects_targets_from_another_frame() -> None:
    frame = _frame()

    with pytest.raises(ValueError, match="different prepared frame"):
        frame.handle_event(object(), GameScreenTargets())
