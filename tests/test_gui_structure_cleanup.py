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
