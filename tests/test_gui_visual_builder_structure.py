from __future__ import annotations

import ast
from pathlib import Path


def test_public_game_visual_builder_remains_orchestration_only() -> None:
    source = Path("src/row_taker/gui/game_visual_builder.py").read_text()
    module = ast.parse(source)

    function_names = [
        node.name
        for node in module.body
        if isinstance(node, ast.FunctionDef)
    ]

    assert function_names == ["build_game_visual_state"]
    assert len(source.splitlines()) < 120
