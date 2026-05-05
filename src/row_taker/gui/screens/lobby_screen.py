from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.actions import (
    ClientActionAssignSelfToSeat,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionStartGame,
)
from row_taker.client.state import ClientState, enter_lobby_submenu
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import (
    ACCENT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    WINDOW_BACKGROUND,
    PrimitiveDrawer,
)
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import LobbySeatView

BACKGROUND_TOP = pygame.Color(17, 24, 39)
BACKGROUND_BOTTOM = pygame.Color(10, 14, 23)
PANEL_FILL = pygame.Color(24, 31, 44)
PANEL_FILL_SOFT = pygame.Color(31, 41, 57)
PANEL_BORDER = pygame.Color(75, 91, 118)
PANEL_BORDER_ACTIVE = pygame.Color(125, 190, 255)
BUTTON_FILL = pygame.Color(45, 109, 184)
BUTTON_FILL_HOVER = pygame.Color(68, 139, 220)
BUTTON_FILL_START = pygame.Color(46, 145, 86)
BUTTON_FILL_START_HOVER = pygame.Color(61, 174, 106)
BUTTON_FILL_DANGER = pygame.Color(167, 65, 74)
BUTTON_FILL_DANGER_HOVER = pygame.Color(201, 84, 94)
SEAT_EMPTY = pygame.Color(36, 45, 60)
SEAT_HUMAN = pygame.Color(36, 84, 120)
SEAT_SELF = pygame.Color(49, 120, 156)
SEAT_BOT = pygame.Color(116, 82, 40)
SEAT_SELECTED = pygame.Color(78, 110, 148)
GOLD = pygame.Color(232, 190, 90)
GREEN = pygame.Color(95, 205, 132)
DANGER = pygame.Color(255, 120, 128)


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
class LobbyScreenTargets:
    seat_targets: tuple[SeatTarget, ...] = ()
    button_targets: tuple[LobbyButtonTarget, ...] = ()


@dataclass(frozen=True, slots=True)
class LobbyScreen:
    state: ClientState
    frame_count: int
    last_action_summary: str

    def build_targets(self, layout: DemoLayout) -> LobbyScreenTargets:
        return build_lobby_screen_targets(layout, self.state)

    def handle_event(
        self,
        event: pygame.event.Event,
        targets: LobbyScreenTargets | None,
    ) -> ScreenResult:
        return handle_lobby_event(event, state=self.state, lobby_targets=targets)

    def render(
        self,
        screen: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
        layout: DemoLayout,
        targets: LobbyScreenTargets,
    ) -> None:
        render_lobby_screen(
            screen,
            drawer=drawer,
            layout=layout,
            client_state=self.state,
            frame_count=self.frame_count,
            lobby_targets=targets,
            last_action_summary=self.last_action_summary,
        )


def build_lobby_screen_targets(layout: DemoLayout, state: ClientState) -> LobbyScreenTargets:
    return LobbyScreenTargets(
        seat_targets=_build_lobby_seat_targets(layout, state),
        button_targets=_build_lobby_button_targets(layout, state),
    )


def handle_lobby_event(
    event: pygame.event.Event,
    *,
    state: ClientState | None,
    lobby_targets: LobbyScreenTargets | None,
) -> ScreenResult:
    if event.type == pygame.QUIT:
        return ScreenResult(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return ScreenResult(request_quit=True)
    if state is None or lobby_targets is None:
        return NO_SCREEN_RESULT
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_left_click(event.pos, state=state, lobby_targets=lobby_targets)
    return NO_SCREEN_RESULT


def render_lobby_screen(
    screen: pygame.Surface,
    *,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    lobby_targets: LobbyScreenTargets,
    last_action_summary: str,
) -> None:
    _draw_background(screen)
    _draw_title_bar(screen, drawer, layout, client_state)
    _draw_seat_area(screen, drawer, layout, client_state, lobby_targets)
    _draw_side_panel(screen, drawer, layout, client_state, frame_count, last_action_summary)
    _draw_bottom_bar(screen, drawer, layout, client_state, lobby_targets)


def _handle_left_click(
    position: tuple[int, int],
    *,
    state: ClientState,
    lobby_targets: LobbyScreenTargets,
) -> ScreenResult:
    for target in lobby_targets.seat_targets:
        if target.rect.collidepoint(position):
            next_state = enter_lobby_submenu(state, "seat_edit", selected_seat_index=target.seat_index)
            return ScreenResult(next_state=next_state)

    for target in lobby_targets.button_targets:
        if target.rect.collidepoint(position):
            return _map_lobby_button(target.button_id, state)

    return NO_SCREEN_RESULT


def _map_lobby_button(button_id: str, state: ClientState) -> ScreenResult:
    selected_seat_index = state.navigation_state.selected_seat_index
    if button_id == "start_game":
        return ScreenResult(client_action=ClientActionStartGame())
    if button_id == "back":
        return ScreenResult(next_state=enter_lobby_submenu(state, "main"))
    if selected_seat_index is None:
        return NO_SCREEN_RESULT
    if button_id == "take_seat":
        return ScreenResult(client_action=ClientActionAssignSelfToSeat(seat_index=selected_seat_index))
    if button_id == "create_bot":
        return ScreenResult(
            client_action=ClientActionCreateBot(
                seat_index=selected_seat_index,
                name=f"Bot_{selected_seat_index + 1}",
            )
        )
    if button_id == "clear_seat":
        return ScreenResult(client_action=ClientActionClearSeat(seat_index=selected_seat_index))
    return NO_SCREEN_RESULT


def _build_lobby_seat_targets(layout: DemoLayout, state: ClientState) -> tuple[SeatTarget, ...]:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return ()

    board_rect = _seat_board_rect(layout)
    columns = 2 if lobby_view.seat_count > 4 else 1
    rows = max(1, (lobby_view.seat_count + columns - 1) // columns)
    gap = 16
    card_width = (board_rect.width - (columns - 1) * gap) // columns
    card_height = min(112, max(76, (board_rect.height - (rows - 1) * gap) // rows))

    targets: list[SeatTarget] = []
    for seat in lobby_view.seats:
        col = seat.seat_index % columns
        row = seat.seat_index // columns
        x = board_rect.left + col * (card_width + gap)
        y = board_rect.top + row * (card_height + gap)
        targets.append(SeatTarget(seat_index=seat.seat_index, rect=pygame.Rect(x, y, card_width, card_height)))
    return tuple(targets)


def _build_lobby_button_targets(layout: DemoLayout, state: ClientState) -> tuple[LobbyButtonTarget, ...]:
    bar = _bottom_bar_rect(layout).inflate(-28, -20)
    button_width = 156
    button_height = 42
    gap = 12
    y = bar.centery - button_height // 2

    buttons: list[LobbyButtonTarget] = [
        LobbyButtonTarget(
            button_id="start_game",
            label="Spiel starten",
            rect=pygame.Rect(bar.right - button_width, y, button_width, button_height),
        )
    ]

    selected_seat_index = state.navigation_state.selected_seat_index
    if selected_seat_index is None:
        return tuple(buttons)

    x = bar.left
    for button_id, label in (
        ("take_seat", "Platz nehmen"),
        ("create_bot", "Bot erzeugen"),
        ("clear_seat", "Platz leeren"),
        ("back", "Auswahl lösen"),
    ):
        buttons.append(
            LobbyButtonTarget(
                button_id=button_id,
                label=label,
                rect=pygame.Rect(x, y, button_width, button_height),
            )
        )
        x += button_width + gap

    return tuple(buttons)


def _draw_background(screen: pygame.Surface) -> None:
    screen.fill(WINDOW_BACKGROUND)
    height = max(1, screen.get_height())
    for y in range(height):
        t = y / height
        color = BACKGROUND_TOP.lerp(BACKGROUND_BOTTOM, t)
        pygame.draw.line(screen, color, (0, y), (screen.get_width(), y))


def _draw_title_bar(screen: pygame.Surface, drawer: PrimitiveDrawer, layout: DemoLayout, state: ClientState) -> None:
    rect = layout.header_rect
    _draw_panel(screen, rect, radius=18)
    drawer.draw_text(screen, "Row-Taker Lobby", (rect.left + 24, rect.top + 16), role="title")

    lobby_view = state.lobby_view
    endpoint = "-" if lobby_view is None else lobby_view.server_endpoint or "-"
    own_id = state.own_client_id or "-"
    drawer.draw_text(screen, f"Server: {endpoint}", (rect.left + 24, rect.top + 48), role="small", color=TEXT_MUTED)
    drawer.draw_text(screen, f"client_id: {own_id}", (rect.right - 255, rect.top + 24), role="small", color=TEXT_MUTED)


def _draw_seat_area(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    targets: LobbyScreenTargets,
) -> None:
    panel_rect = _main_lobby_rect(layout)
    _draw_panel(screen, panel_rect, radius=22)
    drawer.draw_text(screen, "Sitzplätze", (panel_rect.left + 24, panel_rect.top + 20), role="title")
    drawer.draw_text(
        screen,
        "Klicken: Platz auswählen · Danach Aktion unten wählen",
        (panel_rect.left + 24, panel_rect.top + 52),
        role="small",
        color=TEXT_MUTED,
    )

    lobby_view = state.lobby_view
    if lobby_view is None:
        drawer.draw_text(screen, "Noch keine Lobby-Daten empfangen.", (panel_rect.left + 24, panel_rect.top + 96))
        return

    mouse_pos = pygame.mouse.get_pos()
    seats_by_index = {seat.seat_index: seat for seat in lobby_view.seats}
    for target in targets.seat_targets:
        seat = seats_by_index[target.seat_index]
        selected = state.navigation_state.selected_seat_index == target.seat_index
        hovered = target.rect.collidepoint(mouse_pos)
        _draw_seat_card(screen, drawer, target.rect, seat, state, selected=selected, hovered=hovered)


def _draw_seat_card(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    seat: LobbySeatView,
    state: ClientState,
    *,
    selected: bool,
    hovered: bool,
) -> None:
    is_self = seat.occupant_client_id is not None and seat.occupant_client_id == state.own_client_id
    fill = _seat_fill_color(seat, is_self=is_self)
    if selected:
        fill = SEAT_SELECTED
    if hovered:
        fill = fill.lerp(pygame.Color(255, 255, 255), 0.10)

    pygame.draw.rect(screen, fill, rect, border_radius=16)
    border = PANEL_BORDER_ACTIVE if selected or hovered else PANEL_BORDER
    pygame.draw.rect(screen, border, rect, width=2 if selected else 1, border_radius=16)

    header = f"Platz {seat.seat_index + 1}"
    drawer.draw_text(screen, header, (rect.left + 16, rect.top + 12), role="body")

    occupant = seat.occupant_display_name or "frei"
    name_color = TEXT_PRIMARY if seat.occupant_display_name is not None else TEXT_MUTED
    drawer.draw_text(screen, occupant, (rect.left + 16, rect.top + 42), role="title", color=name_color)

    kind_label = _seat_kind_label(seat, is_self=is_self)
    badge_rect = pygame.Rect(rect.right - 112, rect.top + 14, 92, 28)
    _draw_badge(screen, drawer, badge_rect, kind_label, selected=selected or is_self)

    if selected:
        drawer.draw_text(screen, "ausgewählt", (rect.left + 16, rect.bottom - 28), role="small", color=GOLD)
    elif seat.occupant_display_name is None:
        drawer.draw_text(screen, "bereit für Mensch oder Bot", (rect.left + 16, rect.bottom - 28), role="small", color=TEXT_MUTED)
    else:
        drawer.draw_text(screen, "belegt", (rect.left + 16, rect.bottom - 28), role="small", color=TEXT_MUTED)


def _draw_side_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    frame_count: int,
    last_action_summary: str,
) -> None:
    rect = _side_lobby_rect(layout)
    _draw_panel(screen, rect, radius=22)
    content_left = rect.left + 20
    y = rect.top + 20
    drawer.draw_text(screen, "Teilnehmer", (content_left, y), role="title")
    y += 42

    lobby_view = state.lobby_view
    if lobby_view is None:
        drawer.draw_text(screen, "Keine Daten", (content_left, y), role="small", color=TEXT_MUTED)
        return

    for participant in lobby_view.participants:
        seat_label = "-" if participant.seat_index is None else str(participant.seat_index + 1)
        is_self = participant.client_id == state.own_client_id
        icon = "●" if participant.participant_kind == ParticipantKind.HUMAN else "◆"
        color = GREEN if is_self else TEXT_PRIMARY
        drawer.draw_text(screen, f"{icon} {participant.display_name}", (content_left, y), role="body", color=color)
        drawer.draw_text(
            screen,
            f"{participant.participant_kind.value} · Platz {seat_label}",
            (content_left + 22, y + 24),
            role="small",
            color=TEXT_MUTED,
        )
        y += 58
        if y > rect.bottom - 170:
            break

    info_top = max(y + 12, rect.bottom - 152)
    drawer.draw_text(screen, "Status", (content_left, info_top), role="small", color=TEXT_MUTED)
    drawer.draw_text(screen, state.pending_action.value, (content_left, info_top + 24), role="body")
    drawer.draw_text(screen, f"Frame {frame_count}", (content_left, info_top + 52), role="small", color=TEXT_MUTED)

    action_rect = pygame.Rect(content_left, info_top + 80, rect.width - 40, 58)
    drawer.draw_wrapped_lines(screen, [last_action_summary], action_rect, role="small", color=TEXT_MUTED)


def _draw_bottom_bar(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    targets: LobbyScreenTargets,
) -> None:
    rect = _bottom_bar_rect(layout)
    _draw_panel(screen, rect, radius=18)

    selected = state.navigation_state.selected_seat_index
    hint = "Kein Platz ausgewählt." if selected is None else f"Platz {selected + 1} ausgewählt."
    drawer.draw_text(screen, hint, (rect.left + 24, rect.top + 10), role="small", color=TEXT_MUTED)

    flash = state.flash_message.text if state.flash_message is not None else None
    if flash:
        drawer.draw_text(screen, flash, (rect.left + 24, rect.bottom - 26), role="small", color=DANGER)

    mouse_pos = pygame.mouse.get_pos()
    for target in targets.button_targets:
        hovered = target.rect.collidepoint(mouse_pos)
        _draw_button(screen, drawer, target, hovered=hovered)


def _draw_button(screen: pygame.Surface, drawer: PrimitiveDrawer, target: LobbyButtonTarget, *, hovered: bool) -> None:
    if target.button_id == "start_game":
        fill = BUTTON_FILL_START_HOVER if hovered else BUTTON_FILL_START
    elif target.button_id == "clear_seat":
        fill = BUTTON_FILL_DANGER_HOVER if hovered else BUTTON_FILL_DANGER
    else:
        fill = BUTTON_FILL_HOVER if hovered else BUTTON_FILL

    pygame.draw.rect(screen, fill, target.rect, border_radius=12)
    pygame.draw.rect(screen, pygame.Color(210, 225, 245), target.rect, width=1, border_radius=12)
    text_pos = _centered_text_position(drawer, target.label, target.rect, role="small")
    drawer.draw_text(screen, target.label, text_pos, role="small")


def _draw_panel(screen: pygame.Surface, rect: pygame.Rect, *, radius: int) -> None:
    pygame.draw.rect(screen, PANEL_FILL, rect, border_radius=radius)
    pygame.draw.rect(screen, PANEL_BORDER, rect, width=1, border_radius=radius)


def _draw_badge(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    text: str,
    *,
    selected: bool,
) -> None:
    fill = ACCENT if selected else PANEL_FILL_SOFT
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, PANEL_BORDER_ACTIVE if selected else PANEL_BORDER, rect, width=1, border_radius=10)
    drawer.draw_text(screen, text, _centered_text_position(drawer, text, rect, role="tiny"), role="tiny")


def _centered_text_position(drawer: PrimitiveDrawer, text: str, rect: pygame.Rect, *, role: str) -> tuple[int, int]:
    font = drawer._font_for_role(role)
    width, height = font.size(text)
    return (rect.centerx - width // 2, rect.centery - height // 2)


def _seat_kind_label(seat: LobbySeatView, *, is_self: bool) -> str:
    if is_self:
        return "Du"
    if seat.occupant_kind == ParticipantKind.BOT:
        return "Bot"
    if seat.occupant_kind == ParticipantKind.HUMAN:
        return "Mensch"
    return "frei"


def _seat_fill_color(seat: LobbySeatView, *, is_self: bool) -> pygame.Color:
    if is_self:
        return SEAT_SELF
    if seat.occupant_kind == ParticipantKind.BOT:
        return SEAT_BOT
    if seat.occupant_kind == ParticipantKind.HUMAN:
        return SEAT_HUMAN
    return SEAT_EMPTY


def _main_lobby_rect(layout: DemoLayout) -> pygame.Rect:
    return pygame.Rect(
        layout.main_rect.left,
        layout.main_rect.top,
        layout.main_rect.width,
        layout.main_rect.height,
    )


def _side_lobby_rect(layout: DemoLayout) -> pygame.Rect:
    return layout.sidebar_rect


def _bottom_bar_rect(layout: DemoLayout) -> pygame.Rect:
    return layout.footer_rect


def _seat_board_rect(layout: DemoLayout) -> pygame.Rect:
    panel = _main_lobby_rect(layout)
    return pygame.Rect(
        panel.left + 24,
        panel.top + 90,
        panel.width - 48,
        panel.height - 116,
    )
