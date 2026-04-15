from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.state import ClientState
from row_taker.gui_demo.layout import DemoLayout


@dataclass(frozen=True, slots=True)
class SeatTarget:
    seat_index: int
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class LobbyButtonTarget:
    button_id: str
    label: str
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class CardTarget:
    card_value: int
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class RowTarget:
    row_id: object
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class ContinueTarget:
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class InteractionMap:
    seat_targets: tuple[SeatTarget, ...] = ()
    lobby_button_targets: tuple[LobbyButtonTarget, ...] = ()
    card_targets: tuple[CardTarget, ...] = ()
    row_targets: tuple[RowTarget, ...] = ()
    continue_target: ContinueTarget | None = None


def build_session_interaction_map(layout: DemoLayout, state: ClientState) -> InteractionMap:
    if state.client_mode.value == "lobby":
        return InteractionMap(
            seat_targets=_build_lobby_seat_targets(layout, state),
            lobby_button_targets=_build_lobby_button_targets(layout, state),
        )

    return InteractionMap(
        card_targets=_build_card_targets(layout, state),
        row_targets=_build_row_targets(layout, state),
        continue_target=_build_continue_target(layout, state),
    )


def _build_lobby_seat_targets(layout: DemoLayout, state: ClientState) -> tuple[SeatTarget, ...]:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return ()

    seat_rects: list[SeatTarget] = []
    top_rect = layout.main_top_rect.inflate(-24, -24)
    seat_top = top_rect.top + 28
    seat_height = 38
    seat_gap = 10

    for seat in lobby_view.seats:
        seat_rect = pygame.Rect(
            top_rect.left,
            seat_top + seat.seat_index * (seat_height + seat_gap),
            max(200, top_rect.width - 220),
            seat_height,
        )
        seat_rects.append(SeatTarget(seat_index=seat.seat_index, rect=seat_rect))
    return tuple(seat_rects)


def _build_lobby_button_targets(layout: DemoLayout, state: ClientState) -> tuple[LobbyButtonTarget, ...]:
    top_rect = layout.main_top_rect.inflate(-24, -24)
    bottom_rect = layout.main_bottom_rect.inflate(-24, -24)
    selected_seat_index = state.navigation_state.selected_seat_index

    buttons: list[LobbyButtonTarget] = []

    if selected_seat_index is None:
        start_rect = pygame.Rect(top_rect.right - 170, top_rect.top + 28, 150, 34)
        buttons.append(LobbyButtonTarget(button_id="start_game", label="Start game", rect=start_rect))
        return tuple(buttons)

    button_specs = [
        ("take_seat", "Take seat"),
        ("create_bot", "Create bot"),
        ("clear_seat", "Clear seat"),
        ("back", "Back"),
        ("start_game", "Start game"),
    ]

    button_width = 150
    button_height = 34
    button_gap = 10
    x = bottom_rect.left
    y = bottom_rect.bottom - button_height

    for button_id, label in button_specs:
        rect = pygame.Rect(x, y, button_width, button_height)
        buttons.append(LobbyButtonTarget(button_id=button_id, label=label, rect=rect))
        x += button_width + button_gap

    return tuple(buttons)


def _build_card_targets(layout: DemoLayout, state: ClientState) -> tuple[CardTarget, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()

    hand_rect = layout.main_bottom_rect.inflate(-24, -24)

    info_lines = [
        f"player: {player_state.self_player_name()}",
        f"pending_action: {state.pending_action.value}",
        "click a card to send the choice",
    ]
    if player_state.phase_info.phase.value == "choose_row" and player_state.pending_card_value() is not None:
        info_lines.append(f"pending_card: {player_state.pending_card_value()}")

    info_line_height = 22
    info_gap = 6
    info_height = len(info_lines) * info_line_height + max(0, len(info_lines) - 1) * info_gap
    cards_top = hand_rect.top + info_height + 10

    card_width = 78
    card_height = 58
    row_gap = 10
    col_gap = 10
    columns = max(1, hand_rect.width // (card_width + col_gap))

    targets: list[CardTarget] = []
    for index, card in enumerate(player_state.hand):
        row_index = index // columns
        column_index = index % columns
        rect = pygame.Rect(
            hand_rect.left + column_index * (card_width + col_gap),
            cards_top + row_index * (card_height + row_gap),
            card_width,
            card_height,
        )
        targets.append(CardTarget(card_value=card.value, rect=rect))
    return tuple(targets)


def _build_row_targets(layout: DemoLayout, state: ClientState) -> tuple[RowTarget, ...]:
    player_state = state.player_state
    public_state = state.public_state
    if player_state is None or public_state is None:
        return ()
    if player_state.phase_info.phase.value != "choose_row":
        return ()

    top_rect = layout.main_top_rect.inflate(-24, -24)

    info_lines = [
        f"round={public_state.round_no} trick={public_state.trick_no} phase={public_state.phase_info.phase.value}",
        f"message: {public_state.phase_info.message or '-'}",
    ]
    info_line_height = 22
    info_gap = 6
    info_height = len(info_lines) * info_line_height + max(0, len(info_lines) - 1) * info_gap
    rows_top = top_rect.top + info_height + 10

    row_area_height = 132
    row_width = max(120, (top_rect.width - 18) // max(1, len(public_state.rows)))

    selectable = set(player_state.get_selectable_row_ids_for_choose_row())
    targets: list[RowTarget] = []
    for index, row in enumerate(public_state.rows):
        if row.row_id not in selectable:
            continue
        rect = pygame.Rect(
            top_rect.left + index * row_width,
            rows_top,
            row_width - 8,
            row_area_height,
        )
        targets.append(RowTarget(row_id=row.row_id, rect=rect))
    return tuple(targets)


def _build_continue_target(layout: DemoLayout, state: ClientState) -> ContinueTarget | None:
    if not state.pending_presentation_events:
        return None
    rect = pygame.Rect(
        layout.sidebar_rect.left + 20,
        layout.sidebar_rect.bottom - 54,
        layout.sidebar_rect.width - 40,
        34,
    )
    return ContinueTarget(rect=rect)
