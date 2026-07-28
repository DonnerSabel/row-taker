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
        "draw_sidebar_status(",
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


def test_game_renderer_uses_explicit_readable_layer_order() -> None:
    source = _source("rendering/game_renderer.py")
    render_body = source.split("def _draw_game_background", maxsplit=1)[0]
    calls = (
        "_draw_game_background(",
        "draw_rows(",
        "draw_opponent_tiles(",
        "draw_own_player_tile(",
        "draw_hand(",
        "draw_presentation_card_motion(",
        "draw_sidebar_status(",
        "_draw_sidebar_frame(",
    )
    positions = tuple(render_body.find(call) for call in calls)

    assert all(position >= 0 for position in positions)
    assert positions == tuple(sorted(positions))


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


def test_presentation_panel_is_text_only_and_has_no_duplicate_card_strip() -> None:
    state_source = _source("game_visual_state.py")
    presentation_source = _source("presentation_renderer.py")

    panel_source = state_source.split("class VisualPresentationPanel:", maxsplit=1)[1].split(
        "class PlayerPlayAnchor:", maxsplit=1
    )[0]
    assert "card_values" not in panel_source
    assert "_draw_presentation_card_strip" not in presentation_source
    assert "panel.card_values" not in presentation_source


def test_player_tiles_render_visual_active_emphasis() -> None:
    source = _source("rendering/game_hud_renderer.py")

    assert 'player.emphasis == "active"' in source
    assert "PALETTE.panel_border_active if active" in source
    assert "border_width=3 if active else 1" in source
    assert "selected=active" in source
    assert "for active_layer in (False, True)" in source


def test_status_and_presentation_use_only_new_sidebar_regions() -> None:
    hud_source = _source("rendering/game_hud_renderer.py")
    presentation_source = _source("presentation_renderer.py")
    interaction_source = _source("game_interaction.py")

    assert "geometry.sidebar_header_rect" in hud_source
    assert "geometry.presentation_rect" in hud_source
    assert "visual_state.status.action_line" in hud_source
    assert "geometry.overlay_rect" not in hud_source
    assert "status.primary_line" not in hud_source
    assert "status.secondary_line" not in hud_source
    assert "status.hand_prompt" not in hud_source
    assert "geometry.stats_rect" not in presentation_source
    assert "geometry.presentation_rect" not in interaction_source


def test_presentation_advance_uses_global_mouse_click_without_button_or_space() -> None:
    interaction_source = _source("game_interaction.py")
    hud_source = _source("rendering/game_hud_renderer.py")

    assert "ContinueTarget" not in interaction_source
    assert "continue_target" not in interaction_source
    assert "_build_continue_target" not in interaction_source
    assert "pygame.K_SPACE" not in interaction_source
    assert "event.button in (1, 3)" in interaction_source
    assert "draw_button(" not in hud_source
    assert "Weiter [Leertaste]" not in hud_source
