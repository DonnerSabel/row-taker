from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.gui_common.layout import DemoLayout


@dataclass(frozen=True, slots=True)
class LobbyLayoutConfig:
    group_max_width: int = 720
    group_min_width: int = 610
    group_margin_x: int = 48
    group_center_y_offset: int = -14
    panel_gap: int = 12
    participant_width: int = 230
    panel_padding_x: int = 22
    panel_header_height: int = 64
    panel_bottom_padding: int = 20
    seat_row_height: int = 36
    seat_row_gap: int = 8
    action_button_width: int = 150
    action_button_height: int = 44
    action_button_gap: int = 10
    bottom_bar_padding_x: int = 28
    bottom_bar_padding_y: int = 18
    bot_dialog_width: int = 470
    bot_dialog_height: int = 205
    bot_dialog_input_height: int = 48
    bot_dialog_button_width: int = 138
    bot_dialog_button_height: int = 42
    bot_dialog_button_gap: int = 10


DEFAULT_LOBBY_LAYOUT = LobbyLayoutConfig()


@dataclass(frozen=True, slots=True)
class LobbyPanelLayout:
    group_rect: pygame.Rect
    seats_rect: pygame.Rect
    participants_rect: pygame.Rect
    seat_board_rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class BotNameDialogLayout:
    dialog_rect: pygame.Rect
    input_rect: pygame.Rect
    confirm_button_rect: pygame.Rect
    cancel_button_rect: pygame.Rect


def compute_lobby_panel_layout(
    layout: DemoLayout,
    seat_count: int,
    *,
    config: LobbyLayoutConfig = DEFAULT_LOBBY_LAYOUT,
) -> LobbyPanelLayout:
    content_rect = layout.main_rect.union(layout.sidebar_rect)
    group_width = min(config.group_max_width, max(config.group_min_width, content_rect.width - 2 * config.group_margin_x))
    group_width = min(group_width, max(1, content_rect.width - 2 * config.group_margin_x))
    participant_width = min(config.participant_width, max(190, group_width // 3))
    seats_width = group_width - participant_width - config.panel_gap

    group_height = _group_height(max(1, seat_count), config=config)
    max_height = max(240, content_rect.height - 88)
    group_height = min(group_height, max_height)

    group_rect = pygame.Rect(0, 0, group_width, group_height)
    group_rect.centerx = content_rect.centerx
    group_rect.centery = content_rect.centery + config.group_center_y_offset
    group_rect.clamp_ip(content_rect.inflate(-24, -24))

    seats_rect = pygame.Rect(group_rect.left, group_rect.top, seats_width, group_height)
    participants_rect = pygame.Rect(seats_rect.right + config.panel_gap, group_rect.top, participant_width, group_height)
    board_height = max(1, seat_count) * config.seat_row_height + max(0, seat_count - 1) * config.seat_row_gap
    seat_board_rect = pygame.Rect(
        seats_rect.left + config.panel_padding_x,
        seats_rect.top + config.panel_header_height,
        seats_rect.width - 2 * config.panel_padding_x,
        board_height,
    )
    return LobbyPanelLayout(
        group_rect=group_rect,
        seats_rect=seats_rect,
        participants_rect=participants_rect,
        seat_board_rect=seat_board_rect,
    )


def compute_bot_name_dialog_layout(
    layout: DemoLayout,
    *,
    config: LobbyLayoutConfig = DEFAULT_LOBBY_LAYOUT,
) -> BotNameDialogLayout:
    content_rect = layout.main_rect.union(layout.sidebar_rect)
    dialog = pygame.Rect(0, 0, config.bot_dialog_width, config.bot_dialog_height)
    dialog.center = content_rect.center
    dialog.y += 8
    input_rect = pygame.Rect(
        dialog.left + 32,
        dialog.top + 82,
        dialog.width - 64,
        config.bot_dialog_input_height,
    )
    button_y = dialog.bottom - 58
    cancel = pygame.Rect(
        dialog.right - 32 - config.bot_dialog_button_width,
        button_y,
        config.bot_dialog_button_width,
        config.bot_dialog_button_height,
    )
    confirm = pygame.Rect(
        cancel.left - config.bot_dialog_button_gap - config.bot_dialog_button_width,
        button_y,
        config.bot_dialog_button_width,
        config.bot_dialog_button_height,
    )
    return BotNameDialogLayout(
        dialog_rect=dialog,
        input_rect=input_rect,
        confirm_button_rect=confirm,
        cancel_button_rect=cancel,
    )


def bottom_bar_inner_rect(
    layout: DemoLayout,
    *,
    config: LobbyLayoutConfig = DEFAULT_LOBBY_LAYOUT,
) -> pygame.Rect:
    return layout.footer_rect.inflate(-2 * config.bottom_bar_padding_x, -2 * config.bottom_bar_padding_y)


def _group_height(seat_count: int, *, config: LobbyLayoutConfig) -> int:
    rows_height = seat_count * config.seat_row_height + max(0, seat_count - 1) * config.seat_row_gap
    return config.panel_header_height + rows_height + config.panel_bottom_padding
