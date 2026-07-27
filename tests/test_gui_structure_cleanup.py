from __future__ import annotations

from pathlib import Path
from typing import get_type_hints

from row_taker.client.actions import ClientAction
from row_taker.gui.screen_result import ScreenResult


ROOT = Path(__file__).resolve().parents[1]


def test_screen_result_client_action_has_concrete_type() -> None:
    assert get_type_hints(ScreenResult)["client_action"] == ClientAction | None


def test_historical_gui_paths_are_removed() -> None:
    removed_paths = (
        "src/row_taker/gui_common",
        "src/row_taker/gui/legacy_material",
        "src/row_taker/gui/gui_main.py",
        "run_lobby_gui.py",
        "run_row_taker_gui_workbench.py",
    )
    assert all(not (ROOT / path).exists() for path in removed_paths)


def test_source_tree_uses_canonical_gui_names() -> None:
    paths = tuple((ROOT / "src").rglob("*.py")) + tuple((ROOT / "tests").rglob("*.py"))
    source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    legacy_package = "row_taker.gui" + "_common"
    legacy_layout_name = "Demo" + "Layout"
    assert legacy_package not in source
    assert legacy_layout_name not in source


def test_prepared_frames_do_not_accept_external_layout_or_targets() -> None:
    from inspect import signature

    from row_taker.gui.screens.connect_screen import ConnectFrame
    from row_taker.gui.screens.game_screen import GameFrame
    from row_taker.gui.screens.lobby_screen import LobbyFrame

    for frame_type in (ConnectFrame, LobbyFrame, GameFrame):
        assert tuple(signature(frame_type.handle_event).parameters) == ("self", "event")
        assert tuple(signature(frame_type.render).parameters) == ("self", "screen", "drawer")


def test_gui_app_no_longer_orchestrates_screen_targets() -> None:
    app_source = (ROOT / "src/row_taker/gui/app.py").read_text(encoding="utf-8")
    assert ".build_targets(" not in app_source
    assert "handle_event(event, targets)" not in app_source
    assert "layout=layout" not in app_source.split("def _process_current_screen", 1)[1].split("def _prepare_current_screen", 1)[0]



def test_workbench_uses_prepared_frames_instead_of_renderer_helpers() -> None:
    app_source = (ROOT / "src/row_taker/gui_workbench/app.py").read_text(encoding="utf-8")
    assert "render_connect_screen" not in app_source
    assert "render_lobby_screen" not in app_source
    assert "render_game_screen" not in app_source
    assert "ConnectFrame.from_layout" in app_source
    assert "LobbyFrame.from_layout" in app_source
    assert "GameFrame.from_layout" in app_source


def test_gui_uses_single_presentation_frame_counter() -> None:
    roots = (Path("src/row_taker/gui"), Path("src/row_taker/gui_workbench"))
    texts = "\n".join(
        path.read_text(encoding="utf-8")
        for root in roots
        for path in root.rglob("*.py")
    )

    assert "frame_count" not in texts
    assert "presentation_frame_count" not in texts
    assert "--presentation-frame" not in texts
    assert "presentation_elapsed_frames" in texts
