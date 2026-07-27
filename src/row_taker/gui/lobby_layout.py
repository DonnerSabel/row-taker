from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.gui.layout import GuiLayout
from row_taker.gui.menu_layout import DEFAULT_MENU_LAYOUT, MenuLayoutConfig, content_rect


@dataclass(frozen=True, slots=True)
class LobbyPanelLayout:
    group_rect: pygame.Rect
    seats_rect: pygame.Rect
    participants_rect: pygame.Rect
    seat_list_rect: pygame.Rect
    action_rect: pygame.Rect


def compute_lobby_panel_layout(
    layout: GuiLayout,
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
    seat_list_height = row_count * config.control_height + max(
        0, row_count - 1
    ) * config.control_gap
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
    participants = pygame.Rect(
        seats.right + config.panel_gap,
        group.top,
        participants_width,
        group.height,
    )
    seat_list = pygame.Rect(
        seats.left + config.panel_padding_x,
        seats.top + config.lobby_panel_title_height,
        seats.width - 2 * config.panel_padding_x,
        min(
            seat_list_height,
            max(
                1,
                seats.height
                - config.lobby_panel_title_height
                - config.lobby_action_gap
                - config.control_height
                - config.lobby_panel_bottom_padding,
            ),
        ),
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


def row_rects(
    list_rect: pygame.Rect,
    count: int,
    *,
    config: MenuLayoutConfig = DEFAULT_MENU_LAYOUT,
) -> tuple[pygame.Rect, ...]:
    rects: list[pygame.Rect] = []
    for index in range(max(0, count)):
        y = list_rect.top + index * (config.control_height + config.control_gap)
        rects.append(
            pygame.Rect(list_rect.left, y, list_rect.width, config.control_height)
        )
    return tuple(rects)


__all__ = ["LobbyPanelLayout", "compute_lobby_panel_layout", "row_rects"]
