from __future__ import annotations

from dataclasses import dataclass, replace

import pygame

from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import (
    centered_text_position,
    draw_button,
    draw_overlay_panel,
    draw_panel,
    draw_vertical_gradient,
)
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import PrimitiveDrawer
from row_taker.gui_common.ui.connect_form_state import ConnectFormState
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult

CONNECT_FIELD_ORDER = ("host", "port", "display_name")
THEME = DEFAULT_THEME
PALETTE = THEME.palette


@dataclass(frozen=True, slots=True)
class ConnectFieldTarget:
    field_name: str
    label: str
    placeholder: str
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
    """Polished connect screen for the nicer GUI client.

    The demo GUI keeps its own deliberately simple screen. This implementation
    shares only the stable form/result data structures with ``gui_demo``.
    """

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
    panel_width = min(720, max(520, content_rect.width - 96))
    panel_height = min(440, max(390, content_rect.height - 64))
    panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
    panel_rect.center = content_rect.center

    inner_left = panel_rect.left + 42
    inner_top = panel_rect.top + 132
    field_width = panel_rect.width - 84
    field_height = 48
    field_gap = 26

    field_targets = (
        ConnectFieldTarget(
            "host",
            "Server IP",
            "z. B. 127.0.0.1",
            pygame.Rect(inner_left, inner_top, field_width, field_height),
        ),
        ConnectFieldTarget(
            "port",
            "Port",
            "z. B. 8765",
            pygame.Rect(inner_left, inner_top + field_height + field_gap, field_width, field_height),
        ),
        ConnectFieldTarget(
            "display_name",
            "Anzeigename",
            "Name im Spiel",
            pygame.Rect(inner_left, inner_top + 2 * (field_height + field_gap), field_width, field_height),
        ),
    )

    button_y = panel_rect.bottom - 70
    button_targets = (
        ConnectButtonTarget("connect", "Verbinden", pygame.Rect(inner_left, button_y, 172, 44)),
        ConnectButtonTarget("quit", "Beenden", pygame.Rect(inner_left + 188, button_y, 142, 44)),
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

    if form.active_field == "port" and not character.isdigit():
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
            if target.button_id == "connect":
                return ScreenResult(connect_requested=True)
            if target.button_id == "quit":
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
    draw_vertical_gradient(screen, theme=THEME)
    _draw_header(screen, drawer, layout)
    _draw_connect_panel(screen, drawer, connect_form, connect_targets)
    _draw_footer(screen, drawer, layout)


def _draw_header(screen: pygame.Surface, drawer: PrimitiveDrawer, layout: DemoLayout) -> None:
    rect = layout.header_rect
    draw_panel(screen, rect, radius=18, theme=THEME)
    drawer.draw_text(screen, "Row-Taker", (rect.left + 24, rect.top + 14), role="title")
    drawer.draw_text(
        screen,
        "Mit Server verbinden und direkt in die Lobby wechseln.",
        (rect.left + 24, rect.top + 48),
        role="small",
        color=PALETTE.text_muted,
    )


def _draw_connect_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    connect_form: ConnectFormState,
    targets: ConnectScreenTargets,
) -> None:
    panel = targets.panel_rect
    draw_panel(screen, panel, radius=THEME.spacing.large_panel_radius, theme=THEME)

    title_x = panel.left + 42
    drawer.draw_text(screen, "Verbinden", (title_x, panel.top + 28), role="title")
    drawer.draw_text(
        screen,
        "Die Werte entsprechen den Serverdaten aus dem Startfenster.",
        (title_x, panel.top + 64),
        role="small",
        color=PALETTE.text_muted,
    )

    mouse_pos = pygame.mouse.get_pos()
    for target in targets.field_targets:
        active = connect_form.active_field == target.field_name
        hovered = target.rect.collidepoint(mouse_pos)
        value = getattr(connect_form, target.field_name)
        _draw_input_field(
            screen,
            drawer,
            target,
            value=value,
            active=active,
            hovered=hovered,
        )

    status_color = PALETTE.danger if connect_form.error_message else PALETTE.text_muted
    status_text = connect_form.error_message or connect_form.status_message
    status_rect = pygame.Rect(panel.left + 42, panel.bottom - 116, panel.width - 84, 34)
    drawer.draw_wrapped_lines(screen, [status_text], status_rect, role="small", color=status_color)

    for target in targets.button_targets:
        hovered = target.rect.collidepoint(mouse_pos)
        draw_button(
            screen,
            drawer,
            target.rect,
            target.label,
            variant="success" if target.button_id == "connect" else "neutral",
            hovered=hovered,
            theme=THEME,
        )


def _draw_input_field(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    target: ConnectFieldTarget,
    *,
    value: str,
    active: bool,
    hovered: bool,
) -> None:
    label_pos = (target.rect.left, target.rect.top - 22)
    label_color = PALETTE.accent_hover if active else PALETTE.text_muted
    drawer.draw_text(screen, target.label, label_pos, role="small", color=label_color)

    fill = PALETTE.panel_fill_strong
    if hovered:
        fill = fill.lerp(PALETTE.text_primary, 0.05)
    border = PALETTE.accent_hover if active else PALETTE.panel_border
    border_width = 2 if active else 1

    pygame.draw.rect(screen, fill, target.rect, border_radius=12)
    pygame.draw.rect(screen, border, target.rect, width=border_width, border_radius=12)

    display_value = value if value else target.placeholder
    text_color = PALETTE.text_primary if value else PALETTE.text_muted
    drawer.draw_text(screen, display_value, (target.rect.left + 14, target.rect.top + 13), role="body", color=text_color)

    if active:
        _draw_text_cursor(screen, drawer, target.rect, display_value)


def _draw_text_cursor(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    text: str,
) -> None:
    font = drawer._font_for_role("body")
    text_width = font.size(text)[0]
    cursor_x = min(rect.right - 16, rect.left + 14 + text_width + 2)
    cursor_rect = pygame.Rect(cursor_x, rect.top + 11, 2, rect.height - 22)
    pygame.draw.rect(screen, PALETTE.accent_hover, cursor_rect)


def _draw_footer(screen: pygame.Surface, drawer: PrimitiveDrawer, layout: DemoLayout) -> None:
    rect = layout.footer_rect
    draw_overlay_panel(screen, rect, radius=18, alpha=70, theme=THEME)
    hints = "Tab nächstes Feld   ·   Enter verbinden   ·   ESC beenden"
    drawer.draw_text(
        screen,
        hints,
        centered_text_position(drawer, hints, rect, role="small"),
        role="small",
        color=PALETTE.text_muted,
    )


__all__ = [
    "ConnectButtonTarget",
    "ConnectFieldTarget",
    "ConnectFormState",
    "ConnectScreen",
    "ConnectScreenTargets",
    "activate_field",
    "activate_next_field",
    "append_character",
    "backspace",
    "build_connect_screen_targets",
    "handle_connect_event",
    "normalized_connection_values",
    "render_connect_screen",
]
