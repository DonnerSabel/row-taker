from __future__ import annotations

import os
import subprocess
import sys


def _assert_import_does_not_load_pygame(module_name: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in ("src", env.get("PYTHONPATH", "")) if part
    )
    code = (
        f"import {module_name}; "
        "import sys; "
        "assert 'pygame' not in sys.modules, sorted("
        "name for name in sys.modules if name.startswith('pygame')"
        ")"
    )
    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        cwd=".",
        env=env,
    )


def test_game_visual_state_import_does_not_load_pygame() -> None:
    _assert_import_does_not_load_pygame("row_taker.gui.game_visual_state")


def test_game_visual_builder_import_does_not_load_pygame() -> None:
    _assert_import_does_not_load_pygame("row_taker.gui.game_visual_builder")


def test_game_visual_static_import_does_not_load_pygame() -> None:
    _assert_import_does_not_load_pygame("row_taker.gui.game_visual_static")


def test_game_visual_presentations_import_does_not_load_pygame() -> None:
    _assert_import_does_not_load_pygame("row_taker.gui.game_visual_presentations")
