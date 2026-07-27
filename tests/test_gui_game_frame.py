from __future__ import annotations

from unittest.mock import Mock

import pytest

pytest.importorskip("pygame")

from row_taker.gui.game_interaction import GameScreenTargets
from row_taker.gui.layout import compute_layout
from row_taker.gui.screen_result import NO_SCREEN_RESULT
from row_taker.gui.screens import game_frame
from row_taker.gui.screens.game_frame import GameFrame


def _frame(
    *,
    visual_state: object | None = None,
    geometry: object | None = None,
    targets: GameScreenTargets | None = None,
) -> GameFrame:
    return GameFrame(
        visual_state=object() if visual_state is None else visual_state,
        presentation_elapsed_frames=5,
        geometry=object() if geometry is None else geometry,
        targets=GameScreenTargets() if targets is None else targets,
    )


def test_game_frame_prepares_visual_state_geometry_and_targets_once(monkeypatch) -> None:
    layout = compute_layout(1280, 720)
    state = object()
    visual_state = Mock(rows=(object(), object()), hand=(object(),), opponents=())
    geometry = Mock(window_rect=layout.window_rect)
    targets = GameScreenTargets()
    build_visual_state = Mock(return_value=visual_state)
    compute_geometry = Mock(return_value=geometry)
    build_targets = Mock(return_value=targets)
    monkeypatch.setattr(game_frame, "build_game_visual_state", build_visual_state)
    monkeypatch.setattr(game_frame, "compute_board_geometry", compute_geometry)
    monkeypatch.setattr(game_frame, "build_game_screen_targets", build_targets)

    frame = GameFrame.from_layout(
        layout=layout,
        state=state,
        presentation_elapsed_frames=5,
        last_action_summary="test",
        mouse_pos=(123, 456),
    )

    build_visual_state.assert_called_once_with(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=5,
    )
    compute_geometry.assert_called_once_with(
        layout.window_rect.size,
        row_count=2,
        hand_card_count=1,
        opponent_count=0,
    )
    build_targets.assert_called_once_with(
        geometry,
        visual_state,
        mouse_pos=(123, 456),
    )
    assert frame.visual_state is visual_state
    assert frame.geometry is geometry
    assert frame.targets is targets


def test_game_frame_render_uses_its_prepared_visual_state_and_targets(monkeypatch) -> None:
    visual_state = object()
    geometry = object()
    targets = GameScreenTargets()
    screen = object()
    drawer = object()
    render_game_screen = Mock()
    monkeypatch.setattr(game_frame, "render_game_screen", render_game_screen)
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
        presentation_elapsed_frames=5,
    )


def test_game_frame_handle_event_uses_its_visual_state_and_targets(monkeypatch) -> None:
    visual_state = object()
    targets = GameScreenTargets()
    event = object()
    handle_game_event = Mock(return_value=NO_SCREEN_RESULT)
    monkeypatch.setattr(game_frame, "handle_game_event", handle_game_event)
    frame = _frame(visual_state=visual_state, targets=targets)

    assert frame.handle_event(event) is NO_SCREEN_RESULT
    handle_game_event.assert_called_once_with(
        event,
        visual_state=visual_state,
        game_targets=targets,
    )
