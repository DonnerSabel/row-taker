from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from row_taker.gui.screens.game_screen import GameFrame
from row_taker.gui_workbench.app import (
    OFFSCREEN_MOUSE_POS,
    prepare_headless_pygame,
    render_scenario_frame,
    save_scenario_frame,
    save_scenario_frames,
)
from row_taker.gui_workbench.scenarios import get_scenario, scenarios


@pytest.fixture(scope="module", autouse=True)
def initialized_pygame() -> None:
    prepare_headless_pygame()
    yield
    pygame.quit()


def _pixels(surface: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surface, "RGBA")


def test_render_uses_real_game_frame_and_production_targets() -> None:
    rendered = render_scenario_frame(get_scenario("choose-card"), frame_count=7)

    assert isinstance(rendered.game_frame, GameFrame)
    assert rendered.game_frame.frame_count == 7
    assert len(rendered.game_frame.targets.card_targets) == 10
    assert rendered.surface.get_size() == (1600, 900)


def test_identical_inputs_render_pixel_identically() -> None:
    scenario = get_scenario("card-placed")

    first = render_scenario_frame(
        scenario,
        frame_count=16,
        presentation_frame_count=16,
    )
    second = render_scenario_frame(
        scenario,
        frame_count=16,
        presentation_frame_count=16,
    )

    assert _pixels(first.surface) == _pixels(second.surface)


def test_explicit_mouse_position_uses_real_hover_path() -> None:
    scenario = get_scenario("choose-card")
    plain = render_scenario_frame(scenario, mouse_pos=OFFSCREEN_MOUSE_POS)
    first_target = plain.game_frame.targets.card_targets[0]

    hovered = render_scenario_frame(
        scenario,
        mouse_pos=first_target.rect.center,
    )

    assert _pixels(plain.surface) != _pixels(hovered.surface)
    assert hovered.game_frame.targets.card_targets[0].card.hovered is True


@pytest.mark.parametrize("scenario", scenarios(), ids=lambda item: item.name)
def test_every_catalog_scenario_renders_all_interesting_frames(scenario) -> None:
    for frame in scenario.interesting_frames:
        rendered = render_scenario_frame(
            scenario,
            frame_count=frame,
            presentation_frame_count=frame,
        )
        assert rendered.surface.get_size() == scenario.default_size


def test_save_scenario_frame_writes_real_png(tmp_path: Path) -> None:
    output = save_scenario_frame(
        get_scenario("row-taken"),
        tmp_path / "nested" / "row-taken.png",
        frame_count=16,
        presentation_frame_count=16,
    )

    assert output.is_file()
    loaded = pygame.image.load(str(output))
    assert loaded.get_size() == (1600, 900)


def test_save_scenario_frames_uses_interesting_frames_by_default(tmp_path: Path) -> None:
    scenario = get_scenario("card-placed")

    outputs = save_scenario_frames(scenario, tmp_path)

    assert len(outputs) == len(scenario.interesting_frames)
    assert all(output.is_file() for output in outputs)
    assert outputs[0].name == "card-placed_frame_000.png"
    assert outputs[-1].name == "card-placed_frame_032.png"


def test_render_rejects_surface_with_wrong_size() -> None:
    scenario = get_scenario("choose-card")

    with pytest.raises(ValueError, match="does not match requested size"):
        render_scenario_frame(
            scenario,
            size=(1600, 900),
            surface=pygame.Surface((1280, 720)),
        )
