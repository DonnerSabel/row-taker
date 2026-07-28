from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_server_delegates_bot_process_and_match_routing_details() -> None:
    local_server = (ROOT / "src/row_taker/server/local_server.py").read_text(
        encoding="utf-8"
    )

    assert "BotProcessHandle" not in local_server
    assert "validate_submit_card" not in local_server
    assert "validate_submit_row_choice" not in local_server
    assert "_next_game_revision" not in local_server
    assert "_running_bot_processes_by_client_id" not in local_server
    assert "LocalBotManager" in local_server
    assert "MatchSessionRouter" in local_server


def test_extracted_server_components_have_single_primary_responsibilities() -> None:
    bot_manager = (
        ROOT / "src/row_taker/server/local_bot_manager.py"
    ).read_text(encoding="utf-8")
    match_router = (
        ROOT / "src/row_taker/server/match_session_router.py"
    ).read_text(encoding="utf-8")

    assert "class LocalBotManager" in bot_manager
    assert "MatchHub" not in bot_manager
    assert "class MatchSessionRouter" in match_router
    assert "spawn_local_bot" not in match_router
