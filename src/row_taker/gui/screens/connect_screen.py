from __future__ import annotations

from dataclasses import dataclass, replace

import pygame

from row_taker.gui.connect_form_state import ConnectFormState
from row_taker.gui.layout import GuiLayout
from row_taker.gui.menu_layout import DEFAULT_MENU_LAYOUT, compute_connect_panel_layout
from row_taker.gui.menu_shell import (
    draw_menu_background,
    draw_menu_footer,
    draw_menu_header,
    draw_menu_panel,
    draw_text_input,
)
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.screen_result import NO_SCREEN_RESULT, ScreenResult
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_button, draw_overlay_panel

CONNECT_FIELD_ORDER = ("host", "port", "display_name")
THEME = DEFAULT_THEME
PALETTE = THEME.palette
MENU_LAYOUT = DEFAULT_MENU_LAYOUT


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
    error_rect: pygame.Rect
    field_targets: tuple[ConnectFieldTarget, ...]
    button_targets: tuple[ConnectButtonTarget, ...]


@dataclass(frozen=True, slots=True)
class ConnectFrame:
    """One fully prepared production frame of the connect screen."""

    connect_form: ConnectFormState
    layout: GuiLayout
    targets: ConnectScreenTargets
    mouse_pos: tuple[int, int] = (-1, -1)

    @classmethod
    def from_layout(
        cls,
        *,
        layout: GuiLayout,
        connect_form: ConnectFormState,
        mouse_pos: tuple[int, int] | None = None,
    ) -> ConnectFrame:
        return cls(
            connect_form=connect_form,
            layout=layout,
            targets=build_connect_screen_targets(layout),
            mouse_pos=_current_mouse_pos() if mouse_pos is None else mouse_pos,
        )

    def handle_event(self, event: pygame.event.Event) -> ScreenResult:
        return handle_connect_event(
            event,
            connect_form=self.connect_form,
            connect_targets=self.targets,
        )

    def render(
        self,
        screen: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
    ) -> None:
        render_connect_screen(
            screen,
            drawer=drawer,
            layout=self.layout,
            connect_form=self.connect_form,
            connect_targets=self.targets,
            mouse_pos=self.mouse_pos,
        )


def _current_mouse_pos() -> tuple[int, int]:
    try:
        return pygame.mouse.get_pos()
    except pygame.error:
        return (-1, -1)


def build_connect_screen_targets(layout: GuiLayout) -> ConnectScreenTargets:
    panel_layout = compute_connect_panel_layout(layout, field_count=3, button_count=2)
    field_targets = (
        ConnectFieldTarget("host", "Server IP", "z. B. 127.0.0.1", panel_layout.field_rects[0]),
        ConnectFieldTarget("port", "Port", "z. B. 8765", panel_layout.field_rects[1]),
        ConnectFieldTarget("display_name", "Anzeigename", "Name im Spiel", panel_layout.field_rects[2]),
    )
    button_targets = (
        ConnectButtonTarget("connect", "Verbinden", panel_layout.button_rects[0]),
        ConnectButtonTarget("quit", "Beenden", panel_layout.button_rects[1]),
    )
    return ConnectScreenTargets(
        panel_rect=panel_layout.panel_rect,
        error_rect=panel_layout.error_rect,
        field_targets=field_targets,
        button_targets=button_targets,
    )


def activate_field(form: ConnectFormState, field_name: str) -> ConnectFormState:
    should_select_all = field_name in form.auto_select_fields
    return replace(
        form,
        active_field=field_name,
        selected_field=field_name if should_select_all else None,
        error_message=None,
    )


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
    if form.selected_field == form.active_field:
        next_value = character
    else:
        if len(value) >= 40:
            return form
        next_value = value + character

    return replace(
        form,
        **{form.active_field: next_value},
        auto_select_fields=_remove_auto_select_field(form, form.active_field),
        selected_field=None,
        error_message=None,
    )


def backspace(form: ConnectFormState) -> ConnectFormState:
    value = getattr(form, form.active_field)
    if not value and form.selected_field != form.active_field:
        return form
    if form.selected_field == form.active_field:
        next_value = ""
    else:
        next_value = value[:-1]
    return replace(
        form,
        **{form.active_field: next_value},
        auto_select_fields=_remove_auto_select_field(form, form.active_field),
        selected_field=None,
        error_message=None,
    )


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
    layout: GuiLayout,
    connect_form: ConnectFormState,
    connect_targets: ConnectScreenTargets,
    mouse_pos: tuple[int, int],
) -> None:
    draw_menu_background(screen)
    hovered_button_id = _hovered_button_id(connect_targets, mouse_pos)
    draw_menu_header(
        screen,
        drawer,
        layout,
        title="Row-Taker",
        subtitle="Mit Server verbinden und direkt in die Lobby wechseln.",
    )
    _draw_connect_panel(
        screen,
        drawer,
        connect_form,
        connect_targets,
        mouse_pos=mouse_pos,
    )
    draw_menu_footer(
        screen,
        drawer,
        layout,
        text=_footer_hint_text(connect_form, hovered_button_id),
        is_error=connect_form.error_message is not None,
    )


def _draw_connect_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    connect_form: ConnectFormState,
    targets: ConnectScreenTargets,
    *,
    mouse_pos: tuple[int, int],
) -> None:
    panel = targets.panel_rect
    draw_menu_panel(screen, panel)

    title_x = panel.left + MENU_LAYOUT.panel_padding_x
    drawer.draw_text(screen, "Verbinden", (title_x, panel.top + 28), role="title")
    drawer.draw_text(
        screen,
        "Die Werte entsprechen den Serverdaten aus dem Startfenster.",
        (title_x, panel.top + 66),
        role="body",
        color=PALETTE.text_muted,
    )

    for target in targets.field_targets:
        active = connect_form.active_field == target.field_name
        hovered = target.rect.collidepoint(mouse_pos)
        selected = connect_form.selected_field == target.field_name
        value = getattr(connect_form, target.field_name)
        label_pos = (target.rect.left, target.rect.top - MENU_LAYOUT.field_label_gap)
        label_color = PALETTE.accent_hover if active else PALETTE.text_muted
        drawer.draw_text(screen, target.label, label_pos, role="body", color=label_color)
        draw_text_input(
            screen,
            drawer,
            target.rect,
            value=value,
            placeholder=target.placeholder,
            active=active,
            hovered=hovered,
            selected=selected,
        )

    if connect_form.error_message:
        draw_overlay_panel(screen, targets.error_rect, radius=12, alpha=85, theme=THEME)
        drawer.draw_wrapped_lines(
            screen,
            [connect_form.error_message],
            targets.error_rect.inflate(-12, -8),
            role="small",
            color=PALETTE.danger,
            line_gap=4,
        )

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


def _footer_hint_text(connect_form: ConnectFormState, hovered_button_id: str | None) -> str:
    if connect_form.error_message:
        return connect_form.error_message

    if hovered_button_id == "connect":
        return "Enter oder Klick verbindet mit dem Server · Tab nächstes Element · Esc beenden"
    if hovered_button_id == "quit":
        return "Enter oder Klick beendet das Programm · Tab nächstes Element · Esc beenden"

    if connect_form.selected_field == connect_form.active_field:
        return "Tippen ersetzt den Standardwert · Tab nächstes Feld · Enter verbinden · Esc beenden"

    return connect_form.status_message


def _hovered_button_id(
    connect_targets: ConnectScreenTargets,
    mouse_pos: tuple[int, int],
) -> str | None:
    for target in connect_targets.button_targets:
        if target.rect.collidepoint(mouse_pos):
            return target.button_id
    return None


def _remove_auto_select_field(form: ConnectFormState, field_name: str) -> tuple[str, ...]:
    return tuple(name for name in form.auto_select_fields if name != field_name)


__all__ = [
    "ConnectButtonTarget",
    "ConnectFieldTarget",
    "ConnectFormState",
    "ConnectFrame",
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
