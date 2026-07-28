from __future__ import annotations

from pathlib import Path

import pytest

from row_taker.client.core_reducer import apply_ui_action, reduce_server_message
from row_taker.client.state import ClientState

ROOT = Path(__file__).resolve().parents[1]
CLIENT_DIR = ROOT / "src/row_taker/client"


def test_core_reducer_is_only_a_typed_dispatcher() -> None:
    source = (CLIENT_DIR / "core_reducer.py").read_text(encoding="utf-8")

    assert "validate_submit_card" not in source
    assert "validate_submit_row_choice" not in source
    assert "start_trick_presentation" not in source
    assert "apply_trick_row_choice" not in source
    assert "dataclass" not in source
    assert "PendingAction" not in source


def test_reducer_concerns_live_in_dedicated_modules() -> None:
    assert (CLIENT_DIR / "server_transitions.py").is_file()
    assert (CLIENT_DIR / "action_transitions.py").is_file()
    assert (CLIENT_DIR / "presentation_queue.py").is_file()

    state_source = (CLIENT_DIR / "state.py").read_text(encoding="utf-8")
    assert "def append_pending_presentation_steps" not in state_source
    assert "def advance_presentation_queue" not in state_source


def test_unknown_server_message_still_fails_explicitly() -> None:
    with pytest.raises(TypeError, match="unsupported server message type"):
        reduce_server_message(ClientState(), object())  # type: ignore[arg-type]


def test_unknown_client_action_still_fails_explicitly() -> None:
    with pytest.raises(TypeError, match="unsupported client action type"):
        apply_ui_action(ClientState(), object())  # type: ignore[arg-type]
