from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_domain_layers_do_not_catch_all_exceptions() -> None:
    action_transitions = (ROOT / "src/row_taker/client/action_transitions.py").read_text(
        encoding="utf-8"
    )
    local_server = (ROOT / "src/row_taker/server/local_server.py").read_text(encoding="utf-8")

    assert "except Exception" not in action_transitions
    assert "except Exception" not in local_server
    assert "except ClientRequestRejected" in local_server


def test_broad_infrastructure_catches_are_logged() -> None:
    sources = [
        ROOT / "src/row_taker/gui/app.py",
        ROOT / "src/row_taker/gui/live_client.py",
        ROOT / "src/row_taker/server/network_server.py",
    ]

    for path in sources:
        source = path.read_text(encoding="utf-8")
        assert "except Exception" in source
        assert "logger.exception" in source
