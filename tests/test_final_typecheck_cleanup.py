from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/row_taker"


def test_mypy_checks_the_complete_package() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'files = ["src/row_taker"]' in pyproject
    assert "disallow_any_generics = true" in pyproject


def test_no_untargeted_type_ignores_remain_in_product_code() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in SRC.rglob("*.py"))

    assert "# type: ignore" not in source


def test_obsolete_lobby_helpers_and_root_starter_are_removed() -> None:
    lobby_state = (SRC / "engine/lobby/state.py").read_text(encoding="utf-8")

    assert "def is_configured" not in lobby_state
    assert "def seat_for_client" not in lobby_state
    assert not (ROOT / "run_row_taker.py").exists()
