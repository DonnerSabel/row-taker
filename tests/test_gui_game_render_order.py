from __future__ import annotations

from types import SimpleNamespace

import pygame

from row_taker.gui.rendering import game_renderer


def test_render_game_screen_calls_layers_in_visual_order(monkeypatch) -> None:
    calls: list[str] = []

    def record(name: str):
        def fake(*args, **kwargs) -> None:
            calls.append(name)

        return fake

    monkeypatch.setattr(game_renderer, "_draw_game_background", record("background"))
    monkeypatch.setattr(game_renderer, "draw_rows", record("rows"))
    monkeypatch.setattr(game_renderer, "draw_opponent_tiles", record("opponents"))
    monkeypatch.setattr(game_renderer, "draw_own_player_tile", record("own-player"))
    monkeypatch.setattr(game_renderer, "draw_hand", record("hand"))
    monkeypatch.setattr(game_renderer, "player_staged_card_rects", lambda *args: {})
    monkeypatch.setattr(game_renderer, "draw_presentation_card_motion", record("motion"))
    monkeypatch.setattr(game_renderer, "draw_sidebar_header", record("header"))
    monkeypatch.setattr(game_renderer, "_draw_sidebar_frame", record("frame"))

    game_renderer.render_game_screen(
        pygame.Surface((64, 64)),
        drawer=object(),
        geometry=SimpleNamespace(sidebar_rect=pygame.Rect(32, 0, 32, 64)),
        visual_state=object(),
        game_targets=object(),
        presentation_elapsed_frames=0,
        assets=object(),
    )

    assert calls == [
        "background",
        "rows",
        "opponents",
        "own-player",
        "hand",
        "motion",
        "header",
        "frame",
    ]
