from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/row_taker"


def test_local_server_uses_only_public_registry_api() -> None:
    local_server = (SRC / "server/local_server.py").read_text(encoding="utf-8")
    registry = (SRC / "server/client_registry.py").read_text(encoding="utf-8")

    assert "registry.records" not in local_server
    assert "registry._" not in local_server
    assert "RegistryEntry" not in registry
    assert "def validate_display_name" in registry
    assert "def client_ids" in registry
    assert "def is_empty" in registry


def test_gui_modules_do_not_access_private_font_objects() -> None:
    for path in (SRC / "gui").rglob("*.py"):
        if path.name == "primitives.py":
            continue
        assert "_font_for_role" not in path.read_text(encoding="utf-8"), path


def test_removed_dead_helpers_and_primitives_do_not_return() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in SRC.rglob("*.py"))
    for removed_name in (
        "has_visible_presentation",
        "pulsed_color",
        "ease_out_cubic",
        "draw_card_back",
        "format_resolution_steps_for_cli",
        "def get_prompt",
        "def is_finished",
        "WINDOW_BACKGROUND",
        "def draw_key_value",
    ):
        assert removed_name not in source

    primitives = (SRC / "gui/primitives.py").read_text(encoding="utf-8")
    for removed_method in (
        "    def draw_panel(",
        "    def draw_card(",
        "    def draw_badge(",
    ):
        assert removed_method not in primitives


def test_only_current_gui_artwork_is_packaged() -> None:
    assets = SRC / "assets"

    assert (assets / "connect_bg.png").is_file()
    assert not (assets / "board.png").exists()
    assert not (assets / "titel.png").exists()
