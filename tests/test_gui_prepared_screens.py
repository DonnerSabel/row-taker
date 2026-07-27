from __future__ import annotations

from unittest.mock import Mock

import pytest

pytest.importorskip("pygame")

from row_taker.gui.connect_form_state import ConnectFormState
from row_taker.gui.layout import compute_layout
from row_taker.gui.screen_result import NO_SCREEN_RESULT
from row_taker.gui.screens import connect_screen, lobby_screen
from row_taker.gui.screens.connect_screen import ConnectFrame, ConnectScreenTargets
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui.screens.lobby_screen import LobbyFrame, LobbyScreenTargets
from row_taker.gui.screens.prepared_screen import PreparedScreen
from row_taker.gui_workbench.scenarios import get_scenario


def test_connect_frame_prepares_and_owns_layout_and_targets(monkeypatch) -> None:
    layout = compute_layout(1280, 720)
    form = ConnectFormState()
    targets = Mock(spec=ConnectScreenTargets)
    build_targets = Mock(return_value=targets)
    monkeypatch.setattr(connect_screen, "build_connect_screen_targets", build_targets)

    frame = ConnectFrame.from_layout(layout=layout, connect_form=form, mouse_pos=(10, 20))

    build_targets.assert_called_once_with(layout)
    assert frame.layout is layout
    assert frame.targets is targets
    assert frame.mouse_pos == (10, 20)


def test_connect_frame_uses_its_own_prepared_data(monkeypatch) -> None:
    layout = compute_layout(1280, 720)
    form = ConnectFormState()
    targets = Mock(spec=ConnectScreenTargets)
    frame = ConnectFrame(
        connect_form=form,
        layout=layout,
        targets=targets,
        mouse_pos=(30, 40),
    )
    event = object()
    handle = Mock(return_value=NO_SCREEN_RESULT)
    render = Mock()
    monkeypatch.setattr(connect_screen, "handle_connect_event", handle)
    monkeypatch.setattr(connect_screen, "render_connect_screen", render)

    assert frame.handle_event(event) is NO_SCREEN_RESULT
    surface = object()
    drawer = object()
    frame.render(surface, drawer=drawer)

    handle.assert_called_once_with(event, connect_form=form, connect_targets=targets)
    render.assert_called_once_with(
        surface,
        drawer=drawer,
        layout=layout,
        connect_form=form,
        connect_targets=targets,
        mouse_pos=(30, 40),
    )


def test_lobby_frame_prepares_and_owns_layout_and_targets(monkeypatch) -> None:
    layout = compute_layout(1280, 720)
    state = get_scenario("choose-card").state
    targets = Mock(spec=LobbyScreenTargets)
    build_targets = Mock(return_value=targets)
    monkeypatch.setattr(lobby_screen, "build_lobby_screen_targets", build_targets)

    frame = LobbyFrame.from_layout(layout=layout, state=state, mouse_pos=(50, 60))

    build_targets.assert_called_once_with(layout, state)
    assert frame.layout is layout
    assert frame.targets is targets
    assert frame.mouse_pos == (50, 60)


def test_lobby_frame_uses_its_own_prepared_data(monkeypatch) -> None:
    layout = compute_layout(1280, 720)
    state = get_scenario("choose-card").state
    targets = Mock(spec=LobbyScreenTargets)
    frame = LobbyFrame(
        state=state,
        layout=layout,
        targets=targets,
        mouse_pos=(70, 80),
    )
    event = object()
    handle = Mock(return_value=NO_SCREEN_RESULT)
    render = Mock()
    monkeypatch.setattr(lobby_screen, "handle_lobby_event", handle)
    monkeypatch.setattr(lobby_screen, "render_lobby_screen", render)

    assert frame.handle_event(event) is NO_SCREEN_RESULT
    surface = object()
    drawer = object()
    frame.render(surface, drawer=drawer)

    handle.assert_called_once_with(event, state=state, lobby_targets=targets)
    render.assert_called_once_with(
        surface,
        drawer=drawer,
        layout=layout,
        client_state=state,
        lobby_targets=targets,
        mouse_pos=(70, 80),
    )


def test_all_production_frames_follow_prepared_screen_protocol() -> None:
    assert ConnectFrame.handle_event
    assert LobbyFrame.handle_event
    assert GameFrame.handle_event
    assert PreparedScreen.handle_event
