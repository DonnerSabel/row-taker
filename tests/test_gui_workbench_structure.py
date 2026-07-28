from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = ROOT / "src/row_taker/gui_workbench"


def test_workbench_is_split_by_responsibility() -> None:
    expected = {
        "scenario_types.py",
        "scenario_builders.py",
        "connect_scenarios.py",
        "lobby_scenarios.py",
        "game_scenarios.py",
        "scenario_catalog.py",
        "timeline.py",
        "timeline_builders.py",
    }
    assert expected <= {path.name for path in WORKBENCH.glob("*.py")}


def test_public_scenarios_module_is_only_a_compatibility_facade() -> None:
    source = (WORKBENCH / "scenarios.py").read_text(encoding="utf-8")
    assert "def _base_state" not in source
    assert "_SCENARIO_FACTORIES" not in source
    assert "scenario_catalog import" in source
    assert len(source.splitlines()) < 40


def test_timeline_catalog_does_not_construct_the_full_trick() -> None:
    source = (WORKBENCH / "timeline.py").read_text(encoding="utf-8")
    builder_source = (WORKBENCH / "timeline_builders.py").read_text(encoding="utf-8")
    assert "setup_game" not in source
    assert "MatchHub" not in source
    assert "def build_full_trick_timeline" in builder_source
    assert len(source.splitlines()) < 80


def test_product_gui_does_not_import_workbench() -> None:
    product_gui = ROOT / "src/row_taker/gui"
    source = "\n".join(path.read_text(encoding="utf-8") for path in product_gui.rglob("*.py"))
    assert "row_taker.gui_workbench" not in source
