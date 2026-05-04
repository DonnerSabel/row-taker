from __future__ import annotations

from dataclasses import dataclass, replace

import pygame

from row_taker.gui_demo.layout import DemoLayout
from row_taker.gui_demo.primitives import (
    ACCENT,
    PANEL_BORDER,
    PANEL_FILL,
    TEXT_MUTED,
    WINDOW_BACKGROUND,
    PrimitiveDrawer,
)
from row_taker.gui_demo.ui.connect_form_state import ConnectFormState
from row_taker.gui_demo.ui.screen_result import NO_SCREEN_RESULT, ScreenResult

CONNECT_FIELD_ORDER = ('host', 'port', 'display_name')


@dataclass(frozen=True, slots=True)
class ConnectFieldTarget:
    field_name: str
    label: str
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class ConnectButtonTarget:
    button_id: str
    label: str
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class ConnectScreenTargets:
    panel_rect: pygame.Rect
    field_targets: tuple[ConnectFieldTarget, ...]
    button_targets: tuple[ConnectButtonTarget, ...]


@dataclass(frozen=True, slots=True)
class ConnectScreen:
    connect_form: ConnectFormState

    def build_targets(self, layout: DemoLayout) -> ConnectScreenTargets:
        return build_connect_screen_targets(layout)

    def handle_event(
        self,
        event: pygame.event.Event,
        targets: ConnectScreenTargets | None,
    ) -> ScreenResult:
        return handle_connect_event(
            event,
            connect_form=self.connect_form,
            connect_targets=targets,
        )

    def render(
        self,
        screen: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
        layout: DemoLayout,
        targets: ConnectScreenTargets,
    ) -> None:
        render_connect_screen(
            screen,
            drawer=drawer,
            layout=layout,
            connect_form=self.connect_form,
            connect_targets=targets,
        )

    def normalized_connection_values(self) -> tuple[str, int, str] | None:
        return normalized_connection_values(self.connect_form)


def build_connect_screen_targets(layout: DemoLayout) -> ConnectScreenTargets:
    content_rect = layout.main_rect.union(layout.sidebar_rect)
    panel_width = min(640, content_rect.width - 40)
    panel_height = min(360, content_rect.height - 20)
    panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
    panel_rect.center = content_rect.center

    inner_left = panel_rect.left + 24
    inner_top = panel_rect.top + 64
    field_width = panel_rect.width - 48
    field_height = 42
    field_gap = 22

    field_targets = (
        ConnectFieldTarget('host', 'Server IP', pygame.Rect(inner_left, inner_top, field_width, field_height)),
        ConnectFieldTarget(
            'port',
            'Port',
            pygame.Rect(inner_left, inner_top + (field_height + field_gap), field_width, field_height),
        ),
        ConnectFieldTarget(
            'display_name',
            'Anzeigename',
            pygame.Rect(inner_left, inner_top + 2 * (field_height + field_gap), field_width, field_height),
        ),
    )

    button_y = panel_rect.bottom - 62
    button_targets = (
        ConnectButtonTarget('connect', 'Verbinden', pygame.Rect(inner_left, button_y, 150, 36)),
        ConnectButtonTarget('quit', 'Beenden', pygame.Rect(inner_left + 164, button_y, 150, 36)),
    )

    return ConnectScreenTargets(
        panel_rect=panel_rect,
        field_targets=field_targets,
        button_targets=button_targets,
    )


def activate_field(form: ConnectFormState, field_name: str) -> ConnectFormState:
    return replace(form, active_field=field_name, error_message=None)


def activate_next_field(form: ConnectFormState) -> ConnectFormState:
    index = CONNECT_FIELD_ORDER.index(form.active_field)
    next_field = CONNECT_FIELD_ORDER[(index + 1) % len(CONNECT_FIELD_ORDER)]
    return activate_field(form, next_field)


def append_character(form: ConnectFormState, character: str) -> ConnectFormState:
    if len(character) != 1 or not character.isprintable():
        return form

    if form.active_field == 'port' and not character.isdigit():
        return form

    value = getattr(form, form.active_field)
    if len(value) >= 40:
        return form

    return replace(form, **{form.active_field: value + character}, error_message=None)


def backspace(form: ConnectFormState) -> ConnectFormState:
    value = getattr(form, form.active_field)
    if not value:
        return form
    return replace(form, **{form.active_field: value[:-1]}, error_message=None)


def normalized_connection_values(form: ConnectFormState) -> tuple[str, int, str] | None:
    host = form.host.strip()
    display_name = form.display_name.strip()
    port_text = form.port.strip()

    if not host or not display_name:
        return None
    if not port_text.isdigit():
        return None

    port = int(port_text)
    if not (1 <= port <= 65535):
        return None

    return host, port, display_name


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
    drawer.draw_text(screen, 'Verbinden', title_pos, role='title')

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
            'Enter verbinden',
            'ESC beenden',
        ],
        footer_content,
        role='small',
        color=TEXT_MUTED,
    )


__all__ = [
    'ConnectButtonTarget',
    'ConnectFieldTarget',
    'ConnectFormState',
    'ConnectScreen',
    'ConnectScreenTargets',
    'activate_field',
    'activate_next_field',
    'append_character',
    'backspace',
    'build_connect_screen_targets',
    'handle_connect_event',
    'normalized_connection_values',
    'render_connect_screen',
]
