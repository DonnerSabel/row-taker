from __future__ import annotations

import pygame

from row_taker.gui_demo.connect_screen import (
    ConnectFormState,
    ConnectScreenTargets,
    activate_field,
    activate_next_field,
    append_character,
    backspace,
    build_connect_screen_targets,
    normalized_connection_values,
)
from row_taker.gui_demo.layout import DemoLayout
from row_taker.gui_demo.primitives import PrimitiveDrawer
from row_taker.gui_demo.render import render_connect_screen as _render_connect_screen
from row_taker.gui_demo.ui.screen_result import NO_SCREEN_RESULT, ScreenResult


__all__ = [
    'ConnectFormState',
    'ConnectScreenTargets',
    'build_connect_screen_targets',
    'handle_connect_event',
    'normalized_connection_values',
    'render_connect_screen',
]


def handle_connect_event(
    event: pygame.event.Event,
    *,
    connect_form: ConnectFormState,
    connect_targets: ConnectScreenTargets | None,
) -> ScreenResult:
    if event.type == pygame.QUIT:
        return ScreenResult(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return ScreenResult(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
        return ScreenResult(next_connect_form=activate_next_field(connect_form))
    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return ScreenResult(connect_requested=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
        return ScreenResult(next_connect_form=backspace(connect_form))
    if event.type == pygame.KEYDOWN and event.unicode:
        next_form = append_character(connect_form, event.unicode)
        if next_form is not connect_form:
            return ScreenResult(next_connect_form=next_form)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and connect_targets is not None:
        for target in connect_targets.field_targets:
            if target.rect.collidepoint(event.pos):
                return ScreenResult(next_connect_form=activate_field(connect_form, target.field_name))
        for target in connect_targets.button_targets:
            if not target.rect.collidepoint(event.pos):
                continue
            if target.button_id == 'connect':
                return ScreenResult(connect_requested=True)
            if target.button_id == 'quit':
                return ScreenResult(request_quit=True)
    return NO_SCREEN_RESULT


def render_connect_screen(
    screen: pygame.Surface,
    *,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    connect_form: ConnectFormState,
    connect_targets: ConnectScreenTargets,
) -> None:
    _render_connect_screen(
        screen,
        drawer=drawer,
        layout=layout,
        connect_form=connect_form,
        connect_targets=connect_targets,
    )
