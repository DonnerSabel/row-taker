from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pygame
import pytest

from row_taker.client.actions import (
    ClientActionAdvancePresentation,
    ClientActionChooseCard,
    ClientActionChooseRow,
)
from row_taker.gui import game_interaction
from row_taker.gui.game_interaction import (
    GameScreenTargets,
    build_game_screen_targets,
    handle_game_event,
)
from row_taker.gui.screen_result import NO_SCREEN_RESULT
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui_workbench.app import OFFSCREEN_MOUSE_POS, prepare_scenario_frame
from row_taker.gui_workbench.scenarios import get_scenario


def _replace_target_builders(monkeypatch, *, card_targets, row_targets) -> tuple[Mock, Mock]:
    card_builder = Mock(return_value=card_targets)
    row_builder = Mock(return_value=row_targets)
    monkeypatch.setattr(game_interaction, "_build_card_targets", card_builder)
    monkeypatch.setattr(game_interaction, "_build_row_targets", row_builder)
    return card_builder, row_builder


def test_build_game_screen_targets_uses_live_mouse_by_default(monkeypatch) -> None:
    geometry = object()
    state = object()
    mouse_pos = (21, 34)
    get_pos = Mock(return_value=mouse_pos)
    monkeypatch.setattr(game_interaction.pygame.mouse, "get_pos", get_pos)
    card_builder, row_builder = _replace_target_builders(
        monkeypatch,
        card_targets=("card",),
        row_targets=("row",),
    )

    result = build_game_screen_targets(geometry, state)

    assert result == GameScreenTargets(
        card_targets=("card",),
        row_targets=("row",),
    )
    get_pos.assert_called_once_with()
    card_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)
    row_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)


def test_build_game_screen_targets_uses_explicit_mouse_without_reading_pygame(monkeypatch) -> None:
    geometry = object()
    state = object()
    mouse_pos = (-1, -1)
    get_pos = Mock(side_effect=AssertionError("pygame mouse must not be read"))
    monkeypatch.setattr(game_interaction.pygame.mouse, "get_pos", get_pos)
    card_builder, row_builder = _replace_target_builders(
        monkeypatch,
        card_targets=(),
        row_targets=(),
    )

    result = build_game_screen_targets(
        geometry,
        state,
        mouse_pos=mouse_pos,
    )

    assert result == GameScreenTargets()
    get_pos.assert_not_called()
    card_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)
    row_builder.assert_called_once_with(geometry, state, mouse_pos=mouse_pos)


@pytest.mark.parametrize("button", (1, 3))
def test_any_primary_or_secondary_click_advances_waiting_presentation(button: int) -> None:
    frame = prepare_scenario_frame(
        get_scenario("cards-revealed"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    assert isinstance(frame, GameFrame)
    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=button,
            pos=frame.geometry.play_area_rect.center,
        )
    )

    assert isinstance(result.client_action, ClientActionAdvancePresentation)


def test_presentation_click_has_priority_over_game_targets() -> None:
    card_target = Mock()
    visual_state = SimpleNamespace(interaction=SimpleNamespace(can_advance_presentation=True))
    targets = GameScreenTargets(card_targets=(card_target,))

    result = handle_game_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10)),
        visual_state=visual_state,
        game_targets=targets,
    )

    assert isinstance(result.client_action, ClientActionAdvancePresentation)
    card_target.contains_point.assert_not_called()


def test_space_does_not_advance_presentation_anymore() -> None:
    frame = prepare_scenario_frame(
        get_scenario("cards-revealed"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    result = frame.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0))

    assert result is NO_SCREEN_RESULT


def test_right_click_does_nothing_during_normal_card_choice() -> None:
    frame = prepare_scenario_frame(
        get_scenario("choose-card"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=3,
            pos=frame.geometry.play_area_rect.center,
        )
    )

    assert result is NO_SCREEN_RESULT


def test_quit_event_requests_quit_without_prepared_game_state() -> None:
    result = handle_game_event(
        pygame.event.Event(pygame.QUIT),
        visual_state=None,
        game_targets=None,
    )

    assert result.request_quit


def test_escape_requests_quit_without_prepared_game_state() -> None:
    result = handle_game_event(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0),
        visual_state=None,
        game_targets=None,
    )

    assert result.request_quit


def test_left_click_on_exposed_hand_card_chooses_exactly_that_card() -> None:
    frame = prepare_scenario_frame(
        get_scenario("choose-card"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )
    target = frame.targets.card_targets[0]
    click_pos = (target.rect.left + 2, target.rect.top + 2)

    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=click_pos,
        )
    )

    assert result.client_action == ClientActionChooseCard(card_value=target.card_value)


def test_overlapping_hand_cards_choose_the_visually_frontmost_card() -> None:
    frame = prepare_scenario_frame(
        get_scenario("choose-card"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )
    rear_target, front_target = frame.targets.card_targets[-2:]
    click_pos = (front_target.rect.left + 2, front_target.rect.top + 2)

    assert rear_target.rect.collidepoint(click_pos)
    assert front_target.rect.collidepoint(click_pos)

    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=click_pos,
        )
    )

    assert result.client_action == ClientActionChooseCard(card_value=front_target.card_value)


def test_each_selectable_row_click_returns_its_stable_row_id() -> None:
    frame = prepare_scenario_frame(
        get_scenario("choose-row"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    for target in frame.targets.row_targets:
        result = frame.handle_event(
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=target.rect.center,
            )
        )

        assert result.client_action == ClientActionChooseRow(row_id=target.row_id)


def test_left_click_outside_all_targets_does_nothing_in_normal_play() -> None:
    frame = prepare_scenario_frame(
        get_scenario("choose-card"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=frame.geometry.sidebar_header_rect.center,
        )
    )

    assert result is NO_SCREEN_RESULT


def test_middle_click_does_not_advance_waiting_presentation() -> None:
    frame = prepare_scenario_frame(
        get_scenario("cards-revealed"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=2,
            pos=frame.geometry.play_area_rect.center,
        )
    )

    assert result is NO_SCREEN_RESULT


def test_right_click_does_nothing_during_normal_row_choice() -> None:
    frame = prepare_scenario_frame(
        get_scenario("choose-row"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )
    target = frame.targets.row_targets[0]

    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=3,
            pos=target.rect.center,
        )
    )

    assert result is NO_SCREEN_RESULT


def test_mouse_button_release_never_triggers_a_game_action() -> None:
    frame = prepare_scenario_frame(
        get_scenario("cards-revealed"),
        size=(980, 720),
        mouse_pos=OFFSCREEN_MOUSE_POS,
    )

    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            button=1,
            pos=frame.geometry.play_area_rect.center,
        )
    )

    assert result is NO_SCREEN_RESULT
