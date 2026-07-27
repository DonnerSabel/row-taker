from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from row_taker.gui.screens.connect_screen import ConnectFrame
from row_taker.gui.screens.game_screen import GameFrame
from row_taker.gui.screens.lobby_screen import LobbyFrame
from row_taker.gui_workbench.app import (
    OFFSCREEN_MOUSE_POS,
    prepare_headless_pygame,
    prepare_scenario_frame,
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


@pytest.mark.parametrize(
    ("scenario_name", "frame_type"),
    (
        ("connect-default", ConnectFrame),
        ("lobby-waiting", LobbyFrame),
        ("choose-card", GameFrame),
    ),
)
def test_prepare_scenario_frame_uses_real_production_frame(
    scenario_name: str,
    frame_type: type,
) -> None:
    prepared = prepare_scenario_frame(
        get_scenario(scenario_name),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    assert isinstance(prepared, frame_type)


def test_game_render_uses_real_game_frame_and_production_targets() -> None:
    rendered = render_scenario_frame(
        get_scenario("choose-card"), presentation_elapsed_frames=7
    )

    assert isinstance(rendered.prepared_screen, GameFrame)
    assert rendered.prepared_screen.presentation_elapsed_frames == 7
    assert len(rendered.prepared_screen.targets.card_targets) == 10
    assert rendered.surface.get_size() == (1600, 900)


@pytest.mark.parametrize(
    "scenario_name",
    ("connect-error", "lobby-bot-name-edit", "card-placed"),
)
def test_identical_inputs_render_pixel_identically(scenario_name: str) -> None:
    scenario = get_scenario(scenario_name)

    first = render_scenario_frame(
        scenario,
        presentation_elapsed_frames=16,
    )
    second = render_scenario_frame(
        scenario,
        presentation_elapsed_frames=16,
    )

    assert _pixels(first.surface) == _pixels(second.surface)


def test_explicit_mouse_position_uses_real_game_hover_path() -> None:
    scenario = get_scenario("choose-card")
    plain = render_scenario_frame(scenario, mouse_pos=OFFSCREEN_MOUSE_POS)
    assert isinstance(plain.prepared_screen, GameFrame)
    first_target = plain.prepared_screen.targets.card_targets[0]

    hovered = render_scenario_frame(
        scenario,
        mouse_pos=first_target.rect.center,
    )

    assert _pixels(plain.surface) != _pixels(hovered.surface)
    assert isinstance(hovered.prepared_screen, GameFrame)
    assert hovered.prepared_screen.targets.card_targets[0].card.hovered is True


def test_explicit_mouse_position_uses_real_connect_hover_path() -> None:
    scenario = get_scenario("connect-default")
    plain = render_scenario_frame(scenario, mouse_pos=OFFSCREEN_MOUSE_POS)
    assert isinstance(plain.prepared_screen, ConnectFrame)
    connect_button = plain.prepared_screen.targets.button_targets[0]

    hovered = render_scenario_frame(scenario, mouse_pos=connect_button.rect.center)

    assert _pixels(plain.surface) != _pixels(hovered.surface)
    assert isinstance(hovered.prepared_screen, ConnectFrame)
    assert hovered.prepared_screen.mouse_pos == connect_button.rect.center


def test_explicit_mouse_position_uses_real_lobby_hover_path() -> None:
    scenario = get_scenario("lobby-waiting")
    plain = render_scenario_frame(scenario, mouse_pos=OFFSCREEN_MOUSE_POS)
    assert isinstance(plain.prepared_screen, LobbyFrame)
    seat_target = plain.prepared_screen.targets.seat_targets[0]

    hovered = render_scenario_frame(scenario, mouse_pos=seat_target.rect.center)

    assert _pixels(plain.surface) != _pixels(hovered.surface)
    assert isinstance(hovered.prepared_screen, LobbyFrame)
    assert hovered.prepared_screen.mouse_pos == seat_target.rect.center


@pytest.mark.parametrize("scenario", scenarios(), ids=lambda item: item.name)
def test_every_catalog_scenario_renders_all_interesting_frames(scenario) -> None:
    for frame in scenario.interesting_frames:
        rendered = render_scenario_frame(
            scenario,
            presentation_elapsed_frames=frame,
        )
        assert rendered.surface.get_size() == scenario.default_size


def test_save_scenario_frame_writes_real_png(tmp_path: Path) -> None:
    output = save_scenario_frame(
        get_scenario("lobby-full"),
        tmp_path / "nested" / "lobby-full.png",
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
    scenario = get_scenario("connect-default")

    with pytest.raises(ValueError, match="does not match requested size"):
        render_scenario_frame(
            scenario,
            size=(1600, 900),
            surface=pygame.Surface((1280, 720)),
        )
