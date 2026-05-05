from __future__ import annotations

from dataclasses import dataclass, replace

import pygame

from row_taker.gui.assets import DEFAULT_GUI_ASSETS
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
    panel_width = min(780, max(600, content_rect.width - 160))
    panel_height = min(510, max(450, content_rect.height - 48))
    panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
    panel_rect.center = content_rect.center
    panel_rect.y -= 6

    inner_left = panel_rect.left + 48
    inner_top = panel_rect.top + 140
    field_width = panel_rect.width - 96
    field_height = 54
    field_gap = 34

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

    button_y = panel_rect.bottom - 72
    button_targets = (
        ConnectButtonTarget("connect", "Verbinden", pygame.Rect(inner_left, button_y, 184, 46)),
        ConnectButtonTarget("quit", "Beenden", pygame.Rect(inner_left + 200, button_y, 152, 46)),
    )

    return ConnectScreenTargets(
        panel_rect=panel_rect,
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
    layout: DemoLayout,
    connect_form: ConnectFormState,
    connect_targets: ConnectScreenTargets,
) -> None:
    _draw_background(screen)
    hovered_button_id = _hovered_button_id(connect_targets)
    _draw_header(screen, drawer, layout)
    _draw_connect_panel(screen, drawer, connect_form, connect_targets)
    _draw_footer(screen, drawer, layout, connect_form=connect_form, hovered_button_id=hovered_button_id)


def _draw_background(screen: pygame.Surface) -> None:
    background = DEFAULT_GUI_ASSETS.scaled_connect_background(screen.get_width(), screen.get_height())
    if background is None:
        draw_vertical_gradient(screen, theme=THEME)
    else:
        screen.blit(background, (0, 0))

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill(pygame.Color(0, 0, 0, 146))
    screen.blit(overlay, (0, 0))

    top_overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(
        top_overlay,
        pygame.Color(4, 10, 20, 92),
        pygame.Rect(0, 0, screen.get_width(), screen.get_height() // 3),
    )
    screen.blit(top_overlay, (0, 0))


def _draw_header(screen: pygame.Surface, drawer: PrimitiveDrawer, layout: DemoLayout) -> None:
    rect = layout.header_rect.inflate(-4, -10)
    draw_overlay_panel(screen, rect, radius=20, alpha=58, theme=THEME)
    drawer.draw_text(screen, "Row-Taker", (rect.left + 24, rect.top + 10), role="title")
    drawer.draw_text(
        screen,
        "Mit Server verbinden und direkt in die Lobby wechseln.",
        (rect.left + 24, rect.top + 42),
        role="body",
        color=PALETTE.text_muted,
    )


def _draw_connect_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    connect_form: ConnectFormState,
    targets: ConnectScreenTargets,
) -> None:
    panel = targets.panel_rect
    draw_panel(
        screen,
        panel,
        radius=THEME.spacing.large_panel_radius,
        fill=PALETTE.panel_fill_strong,
        border=PALETTE.panel_border_soft,
        alpha=228,
        theme=THEME,
    )

    title_x = panel.left + 48
    drawer.draw_text(screen, "Verbinden", (title_x, panel.top + 28), role="title")
    drawer.draw_text(
        screen,
        "Die Werte entsprechen den Serverdaten aus dem Startfenster.",
        (title_x, panel.top + 66),
        role="body",
        color=PALETTE.text_muted,
    )

    mouse_pos = pygame.mouse.get_pos()
    for target in targets.field_targets:
        active = connect_form.active_field == target.field_name
        hovered = target.rect.collidepoint(mouse_pos)
        selected = connect_form.selected_field == target.field_name
        value = getattr(connect_form, target.field_name)
        _draw_input_field(
            screen,
            drawer,
            target,
            value=value,
            active=active,
            hovered=hovered,
            selected=selected,
        )

    if connect_form.error_message:
        error_rect = pygame.Rect(panel.left + 48, panel.bottom - 130, panel.width - 96, 38)
        draw_overlay_panel(screen, error_rect, radius=12, alpha=85, theme=THEME)
        drawer.draw_wrapped_lines(
            screen,
            [connect_form.error_message],
            error_rect.inflate(-12, -8),
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


def _draw_input_field(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    target: ConnectFieldTarget,
    *,
    value: str,
    active: bool,
    hovered: bool,
    selected: bool,
) -> None:
    label_pos = (target.rect.left, target.rect.top - 28)
    label_color = PALETTE.accent_hover if active else PALETTE.text_muted
    drawer.draw_text(screen, target.label, label_pos, role="body", color=label_color)

    fill = PALETTE.panel_fill
    if hovered:
        fill = fill.lerp(PALETTE.text_primary, 0.04)
    border = PALETTE.accent_hover if active else PALETTE.panel_border
    border_width = 2 if active else 1

    pygame.draw.rect(screen, fill, target.rect, border_radius=14)
    pygame.draw.rect(screen, border, target.rect, width=border_width, border_radius=14)

    display_value = value if value else target.placeholder
    text_color = PALETTE.text_primary if value else PALETTE.text_muted
    text_pos = (target.rect.left + 16, target.rect.top + 14)

    if selected and value:
        _draw_text_selection(screen, drawer, target.rect, value)

    drawer.draw_text(screen, display_value, text_pos, role="body", color=text_color)

    if active and not selected:
        _draw_text_cursor(screen, drawer, target.rect, display_value)


def _draw_text_selection(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    text: str,
) -> None:
    font = drawer._font_for_role("body")
    text_width, text_height = font.size(text)
    selection_rect = pygame.Rect(rect.left + 12, rect.top + 8, text_width + 10, max(30, text_height + 8))
    selection_surface = pygame.Surface(selection_rect.size, pygame.SRCALPHA)
    selection_surface.fill(pygame.Color(80, 132, 212, 120))
    screen.blit(selection_surface, selection_rect)


def _draw_text_cursor(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    text: str,
) -> None:
    font = drawer._font_for_role("body")
    text_width = font.size(text)[0]
    cursor_x = min(rect.right - 16, rect.left + 16 + text_width + 2)
    cursor_rect = pygame.Rect(cursor_x, rect.top + 10, 2, rect.height - 20)
    pygame.draw.rect(screen, PALETTE.accent_hover, cursor_rect)


def _draw_footer(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    *,
    connect_form: ConnectFormState,
    hovered_button_id: str | None,
) -> None:
    rect = layout.footer_rect.inflate(-4, -14)
    draw_overlay_panel(screen, rect, radius=20, alpha=52, theme=THEME)
    hints = _footer_hint_text(connect_form, hovered_button_id)
    color = PALETTE.danger if connect_form.error_message else PALETTE.text_muted
    drawer.draw_text(
        screen,
        hints,
        centered_text_position(drawer, hints, rect, role="body"),
        role="body",
        color=color,
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


def _hovered_button_id(connect_targets: ConnectScreenTargets) -> str | None:
    mouse_pos = pygame.mouse.get_pos()
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
