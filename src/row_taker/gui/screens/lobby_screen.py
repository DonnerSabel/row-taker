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
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import LobbySeatView

THEME = DEFAULT_THEME
PALETTE = THEME.palette


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
            lobby_targets=targets,
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
    lobby_targets: LobbyScreenTargets,
) -> None:
    _draw_background(screen)
    _draw_title_bar(screen, drawer, layout, client_state)
    _draw_seat_area(screen, drawer, layout, client_state, lobby_targets)
    _draw_participants_panel(screen, drawer, layout, client_state)
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

    board_rect = _seat_board_rect(layout, lobby_view.seat_count)
    columns = 2 if lobby_view.seat_count > 1 else 1
    rows = max(1, (lobby_view.seat_count + columns - 1) // columns)
    gap = 16
    card_width = (board_rect.width - (columns - 1) * gap) // columns
    card_height = min(124, max(88, (board_rect.height - (rows - 1) * gap) // rows))

    targets: list[SeatTarget] = []
    for seat in lobby_view.seats:
        col = seat.seat_index % columns
        row = seat.seat_index // columns
        x = board_rect.left + col * (card_width + gap)
        y = board_rect.top + row * (card_height + gap)
        targets.append(SeatTarget(seat_index=seat.seat_index, rect=pygame.Rect(x, y, card_width, card_height)))
    return tuple(targets)


def _build_lobby_button_targets(layout: DemoLayout, state: ClientState) -> tuple[LobbyButtonTarget, ...]:
    bar = _bottom_bar_rect(layout).inflate(-28, -18)
    button_width = 150
    button_height = 44
    gap = 10
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
        ("take_seat", "Nehmen"),
        ("create_bot", "Bot"),
        ("clear_seat", "Leeren"),
        ("back", "Lösen"),
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
    background = DEFAULT_GUI_ASSETS.scaled_connect_background(screen.get_width(), screen.get_height())
    if background is None:
        draw_vertical_gradient(screen, theme=THEME)
    else:
        screen.blit(background, (0, 0))

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill(pygame.Color(0, 0, 0, 128))
    screen.blit(overlay, (0, 0))

    lower_overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(
        lower_overlay,
        pygame.Color(3, 8, 18, 46),
        pygame.Rect(0, screen.get_height() // 2, screen.get_width(), screen.get_height() // 2),
    )
    screen.blit(lower_overlay, (0, 0))


def _draw_title_bar(screen: pygame.Surface, drawer: PrimitiveDrawer, layout: DemoLayout, state: ClientState) -> None:
    rect = layout.header_rect.inflate(-4, -12)
    draw_overlay_panel(screen, rect, radius=20, alpha=50, theme=THEME)
    drawer.draw_text(screen, "Row-Taker Lobby", (rect.left + 24, rect.top + 8), role="title")

    lobby_view = state.lobby_view
    endpoint = "-" if lobby_view is None else lobby_view.server_endpoint or "-"
    drawer.draw_text(
        screen,
        f"Server: {endpoint}",
        (rect.left + 24, rect.top + 40),
        role="body",
        color=PALETTE.text_muted,
    )


def _draw_seat_area(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    targets: LobbyScreenTargets,
) -> None:
    panel_rect = _main_lobby_rect(layout, state)
    draw_panel(
        screen,
        panel_rect,
        radius=THEME.spacing.large_panel_radius,
        fill=PALETTE.panel_fill_strong,
        border=PALETTE.panel_border_soft,
        alpha=168,
        theme=THEME,
    )
    drawer.draw_text(screen, "Sitzplätze", (panel_rect.left + 28, panel_rect.top + 20), role="title")

    lobby_view = state.lobby_view
    if lobby_view is None:
        drawer.draw_text(screen, "Noch keine Lobby-Daten empfangen.", (panel_rect.left + 28, panel_rect.top + 86))
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
    is_empty = seat.occupant_display_name is None
    fill = _seat_fill_color(seat, is_self=is_self)
    if selected:
        fill = PALETTE.seat_selected
    if hovered:
        fill = fill.lerp(pygame.Color(255, 255, 255), 0.09)

    card_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    card_rect = card_surface.get_rect()
    fill_with_alpha = pygame.Color(fill)
    fill_with_alpha.a = 210 if selected or hovered else 156
    pygame.draw.rect(card_surface, fill_with_alpha, card_rect, border_radius=18)
    screen.blit(card_surface, rect)

    border = _seat_border_color(seat, selected=selected, hovered=hovered, is_self=is_self)
    pygame.draw.rect(screen, border, rect, width=2 if selected or hovered else 1, border_radius=18)

    number_text = f"{seat.seat_index + 1}."
    drawer.draw_text(screen, number_text, (rect.left + 18, rect.top + 14), role="subtitle", color=PALETTE.text_muted)

    icon_rect = pygame.Rect(rect.left + 18, rect.top + 52, 36, 36)
    _draw_seat_icon(screen, icon_rect, seat=seat, is_self=is_self)

    occupant = seat.occupant_display_name or "frei"
    name_color = PALETTE.text_primary if not is_empty else PALETTE.text_muted
    drawer.draw_text(screen, occupant, (rect.left + 66, rect.top + 57), role="subtitle", color=name_color)

    if selected:
        _draw_selected_marker(screen, rect)


def _draw_seat_icon(screen: pygame.Surface, rect: pygame.Rect, *, seat: LobbySeatView, is_self: bool) -> None:
    center = rect.center
    if seat.occupant_display_name is None:
        color = PALETTE.panel_border_active
        pygame.draw.circle(screen, pygame.Color(color.r, color.g, color.b, 38), center, 17)
        pygame.draw.circle(screen, color, center, 16, width=2)
        pygame.draw.line(screen, color, (center[0] - 8, center[1]), (center[0] + 8, center[1]), width=2)
        pygame.draw.line(screen, color, (center[0], center[1] - 8), (center[0], center[1] + 8), width=2)
        return

    if seat.occupant_kind == ParticipantKind.BOT:
        color = PALETTE.gold
        head = pygame.Rect(rect.left + 5, rect.top + 6, rect.width - 10, rect.height - 12)
        pygame.draw.rect(screen, pygame.Color(color.r, color.g, color.b, 46), head, border_radius=8)
        pygame.draw.rect(screen, color, head, width=2, border_radius=8)
        pygame.draw.circle(screen, color, (head.left + 9, head.top + 12), 3)
        pygame.draw.circle(screen, color, (head.right - 9, head.top + 12), 3)
        pygame.draw.line(screen, color, (head.left + 9, head.bottom - 9), (head.right - 9, head.bottom - 9), width=2)
        return

    color = PALETTE.green if is_self else PALETTE.accent_hover
    pygame.draw.circle(screen, pygame.Color(color.r, color.g, color.b, 42), (center[0], center[1] - 7), 9)
    pygame.draw.circle(screen, color, (center[0], center[1] - 7), 9, width=2)
    body_rect = pygame.Rect(center[0] - 13, center[1] + 4, 26, 17)
    pygame.draw.rect(screen, pygame.Color(color.r, color.g, color.b, 42), body_rect, border_radius=8)
    pygame.draw.rect(screen, color, body_rect, width=2, border_radius=8)


def _draw_selected_marker(screen: pygame.Surface, rect: pygame.Rect) -> None:
    marker = pygame.Rect(rect.left, rect.top + 10, 5, rect.height - 20)
    pygame.draw.rect(screen, PALETTE.accent_hover, marker, border_radius=3)


def _draw_participants_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
) -> None:
    rect = _participants_rect(layout)
    draw_panel(
        screen,
        rect,
        radius=THEME.spacing.large_panel_radius,
        fill=PALETTE.panel_fill_strong,
        border=PALETTE.panel_border_soft,
        alpha=174,
        theme=THEME,
    )
    content_left = rect.left + 22
    content_width = rect.width - 44
    y = rect.top + 20
    drawer.draw_text(screen, "Teilnehmer", (content_left, y), role="title")
    y += 42

    lobby_view = state.lobby_view
    if lobby_view is None:
        drawer.draw_text(screen, "Keine Daten", (content_left, y), role="body", color=PALETTE.text_muted)
        return

    participants = tuple(
        participant
        for participant in lobby_view.participants
        if participant.participant_kind != ParticipantKind.BOT
    )
    if not participants:
        drawer.draw_text(screen, "Noch keine Spieler verbunden.", (content_left, y), role="body", color=PALETTE.text_muted)
        return

    item_height = 54
    gap = 8
    visible_area_bottom = rect.bottom - 20
    max_visible = max(1, (visible_area_bottom - y + gap) // (item_height + gap))
    visible_participants = participants[:max_visible]
    for participant in visible_participants:
        participant_rect = pygame.Rect(content_left, y, content_width, item_height)
        _draw_participant_card(screen, drawer, participant_rect, participant, own_client_id=state.own_client_id)
        y += item_height + gap

    if len(participants) > len(visible_participants):
        _draw_participants_scroll_hint(screen, rect, total=len(participants), visible=len(visible_participants))


def _draw_participant_card(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    participant: object,
    *,
    own_client_id: str | None,
) -> None:
    is_self = participant.client_id == own_client_id
    fill = PALETTE.panel_fill.lerp(PALETTE.green, 0.10 if is_self else 0.0)
    draw_panel(
        screen,
        rect,
        radius=14,
        fill=fill,
        border=PALETTE.panel_border_active if is_self else PALETTE.panel_border_soft,
        alpha=160,
        theme=THEME,
    )

    icon_rect = pygame.Rect(rect.left + 12, rect.top + 11, 28, 28)
    _draw_participant_icon(screen, icon_rect, kind=participant.participant_kind, highlighted=is_self)
    color = PALETTE.green if is_self else PALETTE.text_primary
    drawer.draw_text(screen, participant.display_name, (rect.left + 50, rect.top + 10), role="body", color=color)

    seat_label = "-" if participant.seat_index is None else f"{participant.seat_index + 1}."
    drawer.draw_text(
        screen,
        f"Sitz {seat_label}",
        (rect.left + 50, rect.top + 32),
        role="small",
        color=PALETTE.text_muted,
    )


def _draw_participant_icon(
    screen: pygame.Surface,
    rect: pygame.Rect,
    *,
    kind: ParticipantKind,
    highlighted: bool,
) -> None:
    color = PALETTE.green if highlighted else PALETTE.accent_hover
    if kind == ParticipantKind.BOT:
        color = PALETTE.gold
        pygame.draw.rect(screen, pygame.Color(color.r, color.g, color.b, 40), rect.inflate(-2, -2), border_radius=6)
        pygame.draw.rect(screen, color, rect.inflate(-2, -2), width=2, border_radius=6)
        return

    center = rect.center
    pygame.draw.circle(screen, pygame.Color(color.r, color.g, color.b, 42), (center[0], center[1] - 5), 6)
    pygame.draw.circle(screen, color, (center[0], center[1] - 5), 6, width=2)
    body_rect = pygame.Rect(center[0] - 9, center[1] + 3, 18, 12)
    pygame.draw.rect(screen, pygame.Color(color.r, color.g, color.b, 42), body_rect, border_radius=6)
    pygame.draw.rect(screen, color, body_rect, width=2, border_radius=6)


def _draw_participants_scroll_hint(screen: pygame.Surface, rect: pygame.Rect, *, total: int, visible: int) -> None:
    track = pygame.Rect(rect.right - 10, rect.top + 66, 3, rect.height - 88)
    if track.height <= 0:
        return
    pygame.draw.rect(screen, pygame.Color(255, 255, 255, 36), track, border_radius=2)
    thumb_height = max(18, int(track.height * visible / total))
    thumb = pygame.Rect(track.left, track.top, track.width, thumb_height)
    pygame.draw.rect(screen, PALETTE.panel_border_active, thumb, border_radius=2)


def _draw_bottom_bar(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    targets: LobbyScreenTargets,
) -> None:
    rect = _bottom_bar_rect(layout).inflate(-4, -14)
    draw_overlay_panel(screen, rect, radius=20, alpha=50, theme=THEME)

    hint = _bottom_hint(state)
    drawer.draw_text(screen, hint, (rect.left + 24, rect.top + 16), role="body", color=PALETTE.text_muted)

    flash = state.flash_message.text if state.flash_message is not None else None
    if flash:
        drawer.draw_text(screen, flash, (rect.left + 24, rect.bottom - 34), role="body", color=PALETTE.danger)

    mouse_pos = pygame.mouse.get_pos()
    for target in targets.button_targets:
        hovered = target.rect.collidepoint(mouse_pos)
        _draw_button(screen, drawer, target, hovered=hovered)


def _bottom_hint(state: ClientState) -> str:
    selected = state.navigation_state.selected_seat_index
    if selected is None:
        return "Wähle einen Sitzplatz. Freie Plätze können belegt oder mit einem Bot vorbereitet werden."
    return f"{selected + 1}. ausgewählt · Aktion unten wählen"


def _draw_button(screen: pygame.Surface, drawer: PrimitiveDrawer, target: LobbyButtonTarget, *, hovered: bool) -> None:
    variant = (
        "success"
        if target.button_id == "start_game"
        else "danger"
        if target.button_id == "clear_seat"
        else "primary"
    )
    draw_button(screen, drawer, target.rect, target.label, variant=variant, hovered=hovered, theme=THEME)


# Keep the old private helper name inside this module while the drawing code is
# moved to row_taker.gui.widgets.
_centered_text_position = centered_text_position


def _seat_border_color(
    seat: LobbySeatView,
    *,
    selected: bool,
    hovered: bool,
    is_self: bool,
) -> pygame.Color:
    if selected or hovered:
        return PALETTE.panel_border_active
    if is_self:
        return PALETTE.green
    if seat.occupant_kind == ParticipantKind.BOT:
        return PALETTE.gold
    if seat.occupant_kind == ParticipantKind.HUMAN:
        return PALETTE.accent_hover
    return PALETTE.panel_border_soft


def _seat_fill_color(seat: LobbySeatView, *, is_self: bool) -> pygame.Color:
    if is_self:
        return PALETTE.seat_self
    if seat.occupant_kind == ParticipantKind.BOT:
        return PALETTE.seat_bot
    if seat.occupant_kind == ParticipantKind.HUMAN:
        return PALETTE.seat_human
    return PALETTE.seat_empty


def _main_lobby_rect(layout: DemoLayout, state: ClientState) -> pygame.Rect:
    lobby_view = state.lobby_view
    seat_count = 4 if lobby_view is None else max(1, lobby_view.seat_count)
    rows = (seat_count + 1) // 2
    needed_height = 88 + rows * 124 + max(0, rows - 1) * 16 + 30
    height = min(max(330, needed_height), max(330, layout.main_rect.height - 120))
    return pygame.Rect(
        layout.main_rect.left,
        layout.main_rect.top,
        layout.main_rect.width,
        height,
    )


def _participants_rect(layout: DemoLayout) -> pygame.Rect:
    height = min(270, max(190, layout.sidebar_rect.height // 3))
    return pygame.Rect(
        layout.sidebar_rect.left,
        layout.sidebar_rect.top,
        layout.sidebar_rect.width,
        height,
    )


def _bottom_bar_rect(layout: DemoLayout) -> pygame.Rect:
    return layout.footer_rect


def _seat_board_rect(layout: DemoLayout, seat_count: int) -> pygame.Rect:
    panel = _main_lobby_rect_for_seat_count(layout, seat_count)
    return pygame.Rect(
        panel.left + 28,
        panel.top + 76,
        panel.width - 56,
        panel.height - 104,
    )


def _main_lobby_rect_for_seat_count(layout: DemoLayout, seat_count: int) -> pygame.Rect:
    rows = (max(1, seat_count) + 1) // 2
    needed_height = 88 + rows * 124 + max(0, rows - 1) * 16 + 30
    height = min(max(330, needed_height), max(330, layout.main_rect.height - 120))
    return pygame.Rect(
        layout.main_rect.left,
        layout.main_rect.top,
        layout.main_rect.width,
        height,
    )
