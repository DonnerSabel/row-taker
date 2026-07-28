from __future__ import annotations

import inspect
import tomllib
from pathlib import Path
from typing import get_type_hints

from row_taker.cli.frontend import FrontendInputResult
from row_taker.client.actions import ClientAction, ClientActionChooseRow
from row_taker.client.trick_presentation_resolver import apply_trick_row_choice
from row_taker.engine.game.models import RowID
from row_taker.gui.rendering.board_renderer import _draw_row_column
from row_taker.protocol.transport import TcpLineTransport

ROOT = Path(__file__).resolve().parents[1]


def test_row_id_is_used_across_action_resolver_and_renderer_boundaries() -> None:
    assert get_type_hints(ClientActionChooseRow)["row_id"] is RowID
    assert get_type_hints(apply_trick_row_choice)["row_id"] is RowID
    assert get_type_hints(_draw_row_column)["row_id"] is RowID


def test_cli_frontend_result_contains_only_client_actions() -> None:
    action_type = get_type_hints(FrontendInputResult)["action"]
    assert action_type == ClientAction | None


def test_tcp_transport_models_closed_resources_as_optional() -> None:
    hints = get_type_hints(TcpLineTransport)
    assert hints["sock"] == __import__("socket").socket | None
    assert "None" in str(hints["reader"])
    assert "None" in str(hints["writer"])


def test_source_tree_has_no_type_ignore_comments() -> None:
    offenders = []
    for path in (ROOT / "src").rglob("*.py"):
        if "type: ignore" in path.read_text(encoding="utf-8"):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_mypy_is_part_of_dev_checks_and_has_explicit_scope() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = config["project"]["optional-dependencies"]["dev"]
    assert any(dependency.startswith("mypy") for dependency in dev_dependencies)

    mypy_config = config["tool"]["mypy"]
    assert mypy_config["files"] == ["src/row_taker"]
    assert mypy_config["disallow_any_generics"] is True
    assert mypy_config["disallow_untyped_defs"] is True
    assert mypy_config["warn_unused_ignores"] is True

    run_checks = (ROOT / "tools" / "run_checks.sh").read_text(encoding="utf-8")
    assert "\nmypy\n" in run_checks


def test_typed_boundary_functions_have_return_annotations() -> None:
    functions = (apply_trick_row_choice, _draw_row_column)
    for function in functions:
        assert inspect.signature(function).return_annotation is not inspect.Signature.empty
