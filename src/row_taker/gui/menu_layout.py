from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.gui_common.layout import DemoLayout


@dataclass(frozen=True, slots=True)
class MenuLayoutConfig:
    """Shared layout rhythm for the polished menu screens.

    Connect and lobby deliberately use the same core dimensions. The connect
    screen is the visual reference, so controls, seat rows, participant rows
    and buttons share one height.
    """

    control_height: int = 54
    control_gap: int = 14
    field_label_gap: int = 28
    button_gap: int = 14
    panel_gap: int = 12
    panel_padding_x: int = 48
    panel_padding_y: int = 32
    panel_title_height: int = 92
    panel_button_bottom: int = 26
    panel_button_width: int = 184
    panel_button_secondary_width: int = 152
    header_inflate_x: int = -4
    header_inflate_y: int = -12
    footer_inflate_x: int = -4
    footer_inflate_y: int = -14
    connect_panel_min_width: int = 600
    connect_panel_max_width: int = 780
    connect_panel_min_height: int = 450
    connect_panel_max_height: int = 510
    lobby_group_min_width: int = 720
    lobby_group_max_width: int = 880
    lobby_group_margin_x: int = 48
    lobby_group_center_y_offset: int = -10
    lobby_participants_width: int = 230
    lobby_panel_title_height: int = 72
    lobby_panel_bottom_padding: int = 26
    lobby_action_gap: int = 16


DEFAULT_MENU_LAYOUT = MenuLayoutConfig()


@dataclass(frozen=True, slots=True)
class MenuHeaderFooterLayout:
    header_rect: pygame.Rect
    footer_rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class ConnectPanelLayout:
    panel_rect: pygame.Rect
    field_rects: tuple[pygame.Rect, ...]
    button_rects: tuple[pygame.Rect, ...]
    error_rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class LobbyPanelLayout:
    group_rect: pygame.Rect
    seats_rect: pygame.Rect
    participants_rect: pygame.Rect
    seat_list_rect: pygame.Rect
    action_rect: pygame.Rect


def content_rect(layout: DemoLayout) -> pygame.Rect:
    return layout.main_rect.union(layout.sidebar_rect)


def header_footer_layout(
    layout: DemoLayout,
    *,
    config: MenuLayoutConfig = DEFAULT_MENU_LAYOUT,
) -> MenuHeaderFooterLayout:
    return MenuHeaderFooterLayout(
        header_rect=layout.header_rect.inflate(config.header_inflate_x, config.header_inflate_y),
        footer_rect=layout.footer_rect.inflate(config.footer_inflate_x, config.footer_inflate_y),
    )


def compute_connect_panel_layout(
    layout: DemoLayout,
    *,
    field_count: int,
    button_count: int,
    config: MenuLayoutConfig = DEFAULT_MENU_LAYOUT,
) -> ConnectPanelLayout:
    area = content_rect(layout)
    panel_width = min(config.connect_panel_max_width, max(config.connect_panel_min_width, area.width - 160))
    panel_height = min(config.connect_panel_max_height, max(config.connect_panel_min_height, area.height - 48))
    panel = pygame.Rect(0, 0, panel_width, panel_height)
    panel.center = area.center
    panel.y -= 6
    panel.clamp_ip(area.inflate(-24, -24))

    inner_left = panel.left + config.panel_padding_x
    field_width = panel.width - 2 * config.panel_padding_x
    first_field_top = panel.top + config.panel_title_height + config.field_label_gap
    vertical_step = config.control_height + config.control_gap + config.field_label_gap
    field_rects = tuple(
        pygame.Rect(inner_left, first_field_top + index * vertical_step, field_width, config.control_height)
        for index in range(field_count)
    )

    button_y = panel.bottom - config.panel_button_bottom - config.control_height
    button_widths = _button_widths(button_count, config=config)
    button_rects: list[pygame.Rect] = []
    x = inner_left
    for width in button_widths:
        button_rects.append(pygame.Rect(x, button_y, width, config.control_height))
        x += width + config.button_gap

    error_rect = pygame.Rect(inner_left, button_y - 52, field_width, 38)
    return ConnectPanelLayout(
        panel_rect=panel,
        field_rects=field_rects,
        button_rects=tuple(button_rects),
        error_rect=error_rect,
    )


def compute_lobby_panel_layout(
    layout: DemoLayout,
    seat_count: int,
    *,
    config: MenuLayoutConfig = DEFAULT_MENU_LAYOUT,
) -> LobbyPanelLayout:
    area = content_rect(layout)
    group_width = min(
        config.lobby_group_max_width,
        max(config.lobby_group_min_width, area.width - 2 * config.lobby_group_margin_x),
    )
    group_width = min(group_width, max(1, area.width - 2 * config.lobby_group_margin_x))
    participants_width = min(config.lobby_participants_width, max(190, group_width // 3))
    seats_width = group_width - participants_width - config.panel_gap

    row_count = max(1, seat_count)
    seat_list_height = row_count * config.control_height + max(0, row_count - 1) * config.control_gap
    group_height = (
        config.lobby_panel_title_height
        + seat_list_height
        + config.lobby_action_gap
        + config.control_height
        + config.lobby_panel_bottom_padding
    )
    max_height = max(260, area.height - 80)
    group_height = min(group_height, max_height)

    group = pygame.Rect(0, 0, group_width, group_height)
    group.centerx = area.centerx
    group.centery = area.centery + config.lobby_group_center_y_offset
    group.clamp_ip(area.inflate(-24, -24))

    seats = pygame.Rect(group.left, group.top, seats_width, group.height)
    participants = pygame.Rect(seats.right + config.panel_gap, group.top, participants_width, group.height)
    seat_list = pygame.Rect(
        seats.left + config.panel_padding_x,
        seats.top + config.lobby_panel_title_height,
        seats.width - 2 * config.panel_padding_x,
        min(seat_list_height, max(1, seats.height - config.lobby_panel_title_height - config.lobby_action_gap - config.control_height - config.lobby_panel_bottom_padding)),
    )
    action = pygame.Rect(
        seats.left + config.panel_padding_x,
        seats.bottom - config.lobby_panel_bottom_padding - config.control_height,
        seats.width - 2 * config.panel_padding_x,
        config.control_height,
    )
    return LobbyPanelLayout(
        group_rect=group,
        seats_rect=seats,
        participants_rect=participants,
        seat_list_rect=seat_list,
        action_rect=action,
    )


def row_rects(list_rect: pygame.Rect, count: int, *, config: MenuLayoutConfig = DEFAULT_MENU_LAYOUT) -> tuple[pygame.Rect, ...]:
    rects: list[pygame.Rect] = []
    for index in range(max(0, count)):
        y = list_rect.top + index * (config.control_height + config.control_gap)
        rects.append(pygame.Rect(list_rect.left, y, list_rect.width, config.control_height))
    return tuple(rects)


def _button_widths(button_count: int, *, config: MenuLayoutConfig) -> tuple[int, ...]:
    if button_count <= 0:
        return ()
    if button_count == 1:
        return (config.panel_button_width,)
    return (config.panel_button_width, *([config.panel_button_secondary_width] * (button_count - 1)))
