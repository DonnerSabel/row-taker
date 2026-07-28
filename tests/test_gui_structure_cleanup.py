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
    from row_taker.gui.screens.game_frame import GameFrame
    from row_taker.gui.screens.lobby_frame import LobbyFrame

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


def test_lobby_screen_is_split_by_responsibility() -> None:
    old_screen = ROOT / "src/row_taker/gui/screens/lobby_screen.py"
    frame_path = ROOT / "src/row_taker/gui/screens/lobby_frame.py"
    interaction_path = ROOT / "src/row_taker/gui/lobby_interaction.py"
    renderer_path = ROOT / "src/row_taker/gui/lobby_renderer.py"

    assert not old_screen.exists()
    assert frame_path.is_file()
    assert interaction_path.is_file()
    assert renderer_path.is_file()
    assert (ROOT / "src/row_taker/gui/lobby_layout.py").is_file()


def test_lobby_geometry_is_not_kept_in_shared_menu_layout() -> None:
    shared_source = (ROOT / "src/row_taker/gui/menu_layout.py").read_text(
        encoding="utf-8"
    )
    lobby_source = (ROOT / "src/row_taker/gui/lobby_layout.py").read_text(
        encoding="utf-8"
    )

    assert "class LobbyPanelLayout" not in shared_source
    assert "def compute_lobby_panel_layout" not in shared_source
    assert "def row_rects" not in shared_source
    assert "class LobbyPanelLayout" in lobby_source
    assert "def compute_lobby_panel_layout" in lobby_source
    assert "def row_rects" in lobby_source


def test_lobby_renderer_contains_no_client_actions_or_state_updates() -> None:
    source = (ROOT / "src/row_taker/gui/lobby_renderer.py").read_text(encoding="utf-8")

    assert "row_taker.client.actions" not in source
    assert "ClientAction" not in source
    assert "enter_lobby_submenu" not in source
    assert "with_feedback_updates" not in source
    assert "with_navigation_updates" not in source


def test_lobby_interaction_contains_no_drawing_code() -> None:
    source = (ROOT / "src/row_taker/gui/lobby_interaction.py").read_text(encoding="utf-8")

    assert "PrimitiveDrawer" not in source
    assert "pygame.Surface" not in source
    assert "draw_menu_" not in source
    assert "draw_button" not in source
    assert "draw_panel" not in source


def test_lobby_frame_only_orchestrates_prepared_lobby_parts() -> None:
    source = (ROOT / "src/row_taker/gui/screens/lobby_frame.py").read_text(encoding="utf-8")

    assert "build_lobby_screen_targets" in source
    assert "handle_lobby_event" in source
    assert "render_lobby_screen" in source
    assert "ClientAction" not in source
    assert "draw_" not in source


def test_removed_dead_client_and_gui_modules_do_not_return() -> None:
    removed_paths = (
        "src/row_taker/gui/constants.py",
        "src/row_taker/cli/screens.py",
        "src/row_taker/client/presentation_text.py",
    )
    assert all(not (ROOT / path).exists() for path in removed_paths)


def test_visual_player_contains_only_data_used_by_the_gui() -> None:
    from dataclasses import fields

    from row_taker.gui.game_visual_state import VisualPlayer

    assert tuple(field.name for field in fields(VisualPlayer)) == (
        "player_id",
        "name",
        "score",
        "is_self",
        "staged_card_value",
        "emphasis",
    )

