from __future__ import annotations

from dataclasses import dataclass, replace

import pygame

from row_taker.gui_demo.layout import DemoLayout


CONNECT_FIELD_ORDER = ("host", "port", "display_name")


@dataclass(frozen=True, slots=True)
class ConnectFormState:
    host: str = "127.0.0.1"
    port: str = "8765"
    display_name: str = "Spieler"
    active_field: str = "display_name"
    error_message: str | None = None
    status_message: str = "Enter verbindet. Tab wechselt zum nächsten Feld."


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
        ConnectFieldTarget("host", "Server IP", pygame.Rect(inner_left, inner_top, field_width, field_height)),
        ConnectFieldTarget(
            "port",
            "Port",
            pygame.Rect(inner_left, inner_top + (field_height + field_gap), field_width, field_height),
        ),
        ConnectFieldTarget(
            "display_name",
            "Anzeigename",
            pygame.Rect(inner_left, inner_top + 2 * (field_height + field_gap), field_width, field_height),
        ),
    )

    button_y = panel_rect.bottom - 62
    button_targets = (
        ConnectButtonTarget("connect", "Verbinden", pygame.Rect(inner_left, button_y, 150, 36)),
        ConnectButtonTarget("quit", "Beenden", pygame.Rect(inner_left + 164, button_y, 150, 36)),
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
