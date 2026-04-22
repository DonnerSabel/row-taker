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
from row_taker.gui_demo.primitives import ACCENT, PANEL_BORDER, PANEL_FILL, TEXT_MUTED, WINDOW_BACKGROUND, PrimitiveDrawer
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
    screen.fill(WINDOW_BACKGROUND)

    header_content = drawer.draw_panel(screen, layout.header_rect)
    drawer.draw_text(screen, 'Row-Taker GUI Demo', (header_content.left, header_content.top), role='title')
    drawer.draw_text(
        screen,
        'Einfach verbinden und dann direkt spielen.',
        (header_content.left, header_content.top + 34),
        role='small',
        color=TEXT_MUTED,
    )

    pygame.draw.rect(screen, PANEL_FILL, connect_targets.panel_rect)
    pygame.draw.rect(screen, PANEL_BORDER, connect_targets.panel_rect, width=1)

    title_pos = (connect_targets.panel_rect.left + 24, connect_targets.panel_rect.top + 18)
    drawer.draw_text(screen, 'Connect', title_pos, role='title')

    for target in connect_targets.field_targets:
        active = connect_form.active_field == target.field_name
        value = getattr(connect_form, target.field_name)
        label_pos = (target.rect.left, target.rect.top - 18)
        drawer.draw_text(screen, target.label, label_pos, role='small', color=TEXT_MUTED)
        drawer.draw_badge(screen, target.rect, text=value or ' ', active=active)

    for target in connect_targets.button_targets:
        drawer.draw_badge(screen, target.rect, text=target.label, active=(target.button_id == 'connect'))

    status_rect = pygame.Rect(
        connect_targets.panel_rect.left + 24,
        connect_targets.panel_rect.bottom - 114,
        connect_targets.panel_rect.width - 48,
        20,
    )
    drawer.draw_text(screen, connect_form.status_message, (status_rect.left, status_rect.top), role='small', color=TEXT_MUTED)

    if connect_form.error_message is not None:
        error_rect = pygame.Rect(
            connect_targets.panel_rect.left + 24,
            connect_targets.panel_rect.bottom - 88,
            connect_targets.panel_rect.width - 48,
            44,
        )
        drawer.draw_wrapped_lines(screen, [connect_form.error_message], error_rect, role='small', color=ACCENT)

    footer_content = drawer.draw_panel(screen, layout.footer_rect)
    drawer.draw_wrapped_lines(
        screen,
        [
            'Tab nächstes Feld',
            'Enter connect',
            'ESC quit',
        ],
        footer_content,
        role='small',
        color=TEXT_MUTED,
    )
