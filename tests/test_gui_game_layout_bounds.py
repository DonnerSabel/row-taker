from __future__ import annotations

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from row_taker.gui.board_layout import (
    compute_board_geometry,
    hand_card_placements,
    row_card_placements,
)
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui_workbench.app import (
    prepare_headless_pygame,
    prepare_scenario_frame,
    render_scenario_frame,
)
from row_taker.gui_workbench.scenarios import get_scenario

SUPPORTED_GAME_SIZES = (
    (980, 720),
    (1024, 768),
    (1280, 720),
    (1600, 900),
)


@pytest.fixture(scope="module", autouse=True)
def initialized_pygame() -> None:
    prepare_headless_pygame()
    yield
    pygame.quit()


@pytest.mark.parametrize("window_size", SUPPORTED_GAME_SIZES)
def test_row_geometry_stays_inside_play_area_and_above_hand(
    window_size: tuple[int, int],
) -> None:
    geometry = compute_board_geometry(
        window_size,
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )

    assert geometry.play_area_rect.contains(geometry.row_area_rect)
    assert geometry.row_area_rect.bottom < geometry.hand_rect.top

    for column in geometry.row_columns:
        assert geometry.row_area_rect.contains(column)
        assert not column.colliderect(geometry.sidebar_rect)


@pytest.mark.parametrize("window_size", SUPPORTED_GAME_SIZES)
@pytest.mark.parametrize("card_count", (1, 5, 6))
def test_row_cards_never_enter_sidebar_or_hand(
    window_size: tuple[int, int],
    card_count: int,
) -> None:
    geometry = compute_board_geometry(
        window_size,
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )

    for row_index in range(4):
        for placement in row_card_placements(
            geometry,
            row_index=row_index,
            card_count=card_count,
        ):
            assert geometry.window_rect.contains(placement.rect)
            assert not placement.rect.colliderect(geometry.sidebar_rect)
            assert placement.rect.bottom <= geometry.hand_rect.top


@pytest.mark.parametrize("window_size", SUPPORTED_GAME_SIZES)
def test_hand_cards_and_targets_stay_left_of_sidebar(
    window_size: tuple[int, int],
) -> None:
    geometry = compute_board_geometry(
        window_size,
        row_count=4,
        hand_card_count=10,
        opponent_count=5,
    )

    for placement in hand_card_placements(geometry, card_count=10):
        assert placement.rect.right <= geometry.play_area_rect.right
        assert not placement.rect.colliderect(geometry.sidebar_rect)

    frame = prepare_scenario_frame(get_scenario("choose-card"), size=window_size)
    assert isinstance(frame, GameFrame)
    for target in frame.targets.card_targets:
        assert target.rect.right <= frame.geometry.play_area_rect.right
        assert not target.rect.colliderect(frame.geometry.sidebar_rect)


@pytest.mark.parametrize("window_size", SUPPORTED_GAME_SIZES)
def test_row_targets_stay_inside_play_area_and_outside_sidebar(
    window_size: tuple[int, int],
) -> None:
    frame = prepare_scenario_frame(get_scenario("choose-row"), size=window_size)
    assert isinstance(frame, GameFrame)
    assert len(frame.targets.row_targets) == 4

    for target in frame.targets.row_targets:
        assert frame.geometry.play_area_rect.contains(target.rect)
        assert not target.rect.colliderect(frame.geometry.sidebar_rect)
        assert not target.rect.colliderect(frame.geometry.hand_rect)


@pytest.mark.parametrize("window_size", SUPPORTED_GAME_SIZES)
@pytest.mark.parametrize(
    "scenario_name",
    ("cards-revealed", "row-choice-required", "long-names"),
)
def test_layout_stress_scenarios_render_at_supported_sizes(
    window_size: tuple[int, int],
    scenario_name: str,
) -> None:
    rendered = render_scenario_frame(
        get_scenario(scenario_name),
        size=window_size,
        presentation_elapsed_frames=16,
    )

    assert isinstance(rendered.prepared_screen, GameFrame)
    assert rendered.surface.get_size() == window_size
