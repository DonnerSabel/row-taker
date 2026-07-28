from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUI = ROOT / "src/row_taker/gui"


def _source(relative_path: str) -> str:
    return (GUI / relative_path).read_text(encoding="utf-8")


def test_game_screen_module_is_replaced_by_frame_and_rendering_modules() -> None:
    assert not (GUI / "screens/game_screen.py").exists()
    assert (GUI / "screens/game_frame.py").exists()
    assert (GUI / "rendering/game_renderer.py").exists()
    assert (GUI / "rendering/board_renderer.py").exists()
    assert (GUI / "rendering/game_hud_renderer.py").exists()


def test_game_frame_contains_no_drawing_implementation() -> None:
    source = _source("screens/game_frame.py")
    assert "GuiCard" not in source
    assert "pygame.draw" not in source
    assert "draw_rows" not in source
    assert "render_game_screen(" in source


def test_game_renderer_is_a_short_orchestrator() -> None:
    source = _source("rendering/game_renderer.py")
    for call in (
        "draw_rows(",
        "draw_hand(",
        "draw_opponent_tiles(",
        "draw_own_player_tile(",
        "draw_presentation_card_motion(",
        "draw_status_overlay(",
    ):
        assert call in source
    assert "draw_opponent_slots(" not in source
    assert "class GameFrame" not in source


def test_game_renderers_do_not_import_client_or_presentation_event_models() -> None:
    sources = "\n".join(
        _source(path)
        for path in (
            "rendering/game_renderer.py",
            "rendering/board_renderer.py",
            "rendering/game_hud_renderer.py",
            "presentation_renderer.py",
        )
    )
    assert "ClientState" not in sources
    assert "PresentationEvent" not in sources


def test_presentation_renderer_uses_rect_mapping_instead_of_foreign_slot_type() -> None:
    source = _source("presentation_renderer.py")
    assert "Mapping[PlayerID, pygame.Rect]" in source
    assert "OpponentSlot" not in source
    assert "Any" not in source


def test_game_renderer_uses_flat_background_instead_of_board_artwork() -> None:
    source = _source("rendering/game_renderer.py")
    assert "scaled_board_image_full" not in source
    assert "_draw_full_background" not in source
    assert "_draw_game_background(" in source


def test_sidebar_debug_frame_is_drawn_after_all_game_content() -> None:
    source = _source("rendering/game_renderer.py")
    render_body = source.split("def _draw_game_background", maxsplit=1)[0]
    assert render_body.rfind("_draw_sidebar_debug_frame(") > render_body.rfind(
        "draw_own_player_tile("
    )


def test_old_opponent_circles_and_separate_score_list_are_removed() -> None:
    source = _source("rendering/game_hud_renderer.py")
    assert "def draw_opponent_slots" not in source
    assert "pygame.draw.ellipse" not in source
    assert "def _initials" not in source
    assert "def _player_color" not in source
    assert "for player in visual_state.players" not in source


def test_opponent_tiles_use_new_sidebar_geometry() -> None:
    hud_source = _source("rendering/game_hud_renderer.py")
    assert "geometry.opponent_tiles" in hud_source
    assert "geometry.opponent_slots" not in hud_source
    assert "def draw_opponent_tiles" in hud_source
    assert "tile.card_placement.rect" in hud_source


def test_opponent_tile_names_are_fitted_to_pixel_width() -> None:
    source = _source("rendering/game_hud_renderer.py")
    assert "def _fit_text_to_width" in source
    assert "font.size(candidate)[0] <= max_width" in source


def test_own_player_uses_dedicated_sidebar_tile_instead_of_legacy_stats_field() -> None:
    hud_source = _source("rendering/game_hud_renderer.py")
    renderer_source = _source("rendering/game_renderer.py")

    assert "def draw_own_player_tile" in hud_source
    assert "geometry.own_player_tile" in hud_source
    assert "def draw_stats_field" not in hud_source
    assert "draw_stats_field(" not in renderer_source
