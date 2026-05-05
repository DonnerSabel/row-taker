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
    draw_badge,
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
    gap = 18
    card_width = (board_rect.width - (columns - 1) * gap) // columns
    card_height = min(126, max(92, (board_rect.height - (rows - 1) * gap) // rows))

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
    button_width = 164
    button_height = 46
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
    background = DEFAULT_GUI_ASSETS.scaled_connect_background(screen.get_width(), screen.get_height())
    if background is None:
        draw_vertical_gradient(screen, theme=THEME)
    else:
        screen.blit(background, (0, 0))

    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill(pygame.Color(0, 0, 0, 156))
    screen.blit(overlay, (0, 0))

    lower_overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(
        lower_overlay,
        pygame.Color(3, 8, 18, 70),
        pygame.Rect(0, screen.get_height() // 2, screen.get_width(), screen.get_height() // 2),
    )
    screen.blit(lower_overlay, (0, 0))


def _draw_title_bar(screen: pygame.Surface, drawer: PrimitiveDrawer, layout: DemoLayout, state: ClientState) -> None:
    rect = layout.header_rect.inflate(-4, -10)
    draw_overlay_panel(screen, rect, radius=20, alpha=60, theme=THEME)
    drawer.draw_text(screen, "Row-Taker Lobby", (rect.left + 24, rect.top + 10), role="title")

    lobby_view = state.lobby_view
    endpoint = "-" if lobby_view is None else lobby_view.server_endpoint or "-"
    own_id = state.own_client_id or "-"
    drawer.draw_text(
        screen,
        f"Server: {endpoint}",
        (rect.left + 24, rect.top + 42),
        role="body",
        color=PALETTE.text_muted,
    )
    client_text = f"client_id: {own_id}"
    font = drawer._font_for_role("body")
    client_width = font.size(client_text)[0]
    drawer.draw_text(
        screen,
        client_text,
        (rect.right - client_width - 24, rect.top + 26),
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
    panel_rect = _main_lobby_rect(layout)
    draw_panel(
        screen,
        panel_rect,
        radius=THEME.spacing.large_panel_radius,
        fill=PALETTE.panel_fill_strong,
        border=PALETTE.panel_border_soft,
        alpha=218,
        theme=THEME,
    )
    drawer.draw_text(screen, "Sitzplätze", (panel_rect.left + 28, panel_rect.top + 22), role="title")
    drawer.draw_text(
        screen,
        "Klicken: Platz auswählen · Danach Aktion unten wählen",
        (panel_rect.left + 28, panel_rect.top + 58),
        role="body",
        color=PALETTE.text_muted,
    )

    lobby_view = state.lobby_view
    if lobby_view is None:
        drawer.draw_text(screen, "Noch keine Lobby-Daten empfangen.", (panel_rect.left + 28, panel_rect.top + 110))
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
        fill = PALETTE.seat_selected
    if hovered:
        fill = fill.lerp(pygame.Color(255, 255, 255), 0.10)

    card_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    card_rect = card_surface.get_rect()
    fill_with_alpha = pygame.Color(fill)
    fill_with_alpha.a = 222 if selected or hovered else 190
    pygame.draw.rect(card_surface, fill_with_alpha, card_rect, border_radius=18)
    screen.blit(card_surface, rect)

    border = PALETTE.panel_border_active if selected or hovered else PALETTE.panel_border
    pygame.draw.rect(screen, border, rect, width=2 if selected else 1, border_radius=18)

    accent_rect = pygame.Rect(rect.left, rect.top + 12, 4, rect.height - 24)
    accent_color = PALETTE.accent_hover if selected or is_self else PALETTE.panel_border_soft
    pygame.draw.rect(screen, accent_color, accent_rect, border_radius=3)

    header = f"Platz {seat.seat_index + 1}"
    drawer.draw_text(screen, header, (rect.left + 20, rect.top + 14), role="body", color=PALETTE.text_muted)

    occupant = seat.occupant_display_name or "frei"
    name_color = PALETTE.text_primary if seat.occupant_display_name is not None else PALETTE.text_muted
    drawer.draw_text(screen, occupant, (rect.left + 20, rect.top + 46), role="subtitle", color=name_color)

    kind_label = _seat_kind_label(seat, is_self=is_self)
    badge_rect = pygame.Rect(rect.right - 124, rect.top + 16, 100, 30)
    _draw_badge(screen, drawer, badge_rect, kind_label, selected=selected or is_self)

    footer_text = _seat_footer_text(seat, selected=selected)
    footer_color = PALETTE.gold if selected else PALETTE.text_muted
    drawer.draw_text(screen, footer_text, (rect.left + 20, rect.bottom - 34), role="body", color=footer_color)


def _draw_side_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    frame_count: int,
    last_action_summary: str,
) -> None:
    rect = _side_lobby_rect(layout)
    draw_panel(
        screen,
        rect,
        radius=THEME.spacing.large_panel_radius,
        fill=PALETTE.panel_fill_strong,
        border=PALETTE.panel_border_soft,
        alpha=216,
        theme=THEME,
    )
    content_left = rect.left + 22
    content_width = rect.width - 44
    y = rect.top + 22
    drawer.draw_text(screen, "Teilnehmer", (content_left, y), role="title")
    y += 46

    lobby_view = state.lobby_view
    if lobby_view is None:
        drawer.draw_text(screen, "Keine Daten", (content_left, y), role="body", color=PALETTE.text_muted)
        return

    for participant in lobby_view.participants:
        participant_height = 68
        if y + participant_height > rect.bottom - 178:
            break
        participant_rect = pygame.Rect(content_left, y, content_width, participant_height)
        _draw_participant_card(screen, drawer, participant_rect, participant, own_client_id=state.own_client_id)
        y += participant_height + 10

    info_top = max(y + 10, rect.bottom - 160)
    _draw_status_block(
        screen,
        drawer,
        pygame.Rect(content_left, info_top, content_width, rect.bottom - info_top - 18),
        state=state,
        frame_count=frame_count,
        last_action_summary=last_action_summary,
    )


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
        alpha=178,
        theme=THEME,
    )

    seat_label = "-" if participant.seat_index is None else str(participant.seat_index + 1)
    icon = "●" if participant.participant_kind == ParticipantKind.HUMAN else "◆"
    color = PALETTE.green if is_self else PALETTE.text_primary
    drawer.draw_text(screen, f"{icon} {participant.display_name}", (rect.left + 12, rect.top + 10), role="body", color=color)
    drawer.draw_text(
        screen,
        f"{participant.participant_kind.value} · Platz {seat_label}",
        (rect.left + 32, rect.top + 38),
        role="body",
        color=PALETTE.text_muted,
    )


def _draw_status_block(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    state: ClientState,
    frame_count: int,
    last_action_summary: str,
) -> None:
    draw_overlay_panel(screen, rect, radius=16, alpha=64, theme=THEME)
    x = rect.left + 12
    y = rect.top + 12
    drawer.draw_text(screen, "Status", (x, y), role="body", color=PALETTE.text_muted)
    drawer.draw_text(screen, state.pending_action.value, (x, y + 28), role="body")
    drawer.draw_text(screen, f"Frame {frame_count}", (x, y + 56), role="body", color=PALETTE.text_muted)

    action_rect = pygame.Rect(x, y + 86, rect.width - 24, max(36, rect.height - 98))
    drawer.draw_wrapped_lines(screen, [last_action_summary], action_rect, role="body", color=PALETTE.text_muted, line_gap=4)


def _draw_bottom_bar(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    targets: LobbyScreenTargets,
) -> None:
    rect = _bottom_bar_rect(layout).inflate(-4, -14)
    draw_overlay_panel(screen, rect, radius=20, alpha=58, theme=THEME)

    selected = state.navigation_state.selected_seat_index
    hint = "Kein Platz ausgewählt." if selected is None else f"Platz {selected + 1} ausgewählt."
    drawer.draw_text(screen, hint, (rect.left + 24, rect.top + 16), role="body", color=PALETTE.text_muted)

    flash = state.flash_message.text if state.flash_message is not None else None
    if flash:
        drawer.draw_text(screen, flash, (rect.left + 24, rect.bottom - 34), role="body", color=PALETTE.danger)

    mouse_pos = pygame.mouse.get_pos()
    for target in targets.button_targets:
        hovered = target.rect.collidepoint(mouse_pos)
        _draw_button(screen, drawer, target, hovered=hovered)


def _draw_button(screen: pygame.Surface, drawer: PrimitiveDrawer, target: LobbyButtonTarget, *, hovered: bool) -> None:
    variant = (
        "success"
        if target.button_id == "start_game"
        else "danger"
        if target.button_id == "clear_seat"
        else "primary"
    )
    draw_button(screen, drawer, target.rect, target.label, variant=variant, hovered=hovered, theme=THEME)


def _draw_badge(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    text: str,
    *,
    selected: bool,
) -> None:
    draw_badge(screen, drawer, rect, text, active=selected, theme=THEME)


# Keep the old private helper name inside this module while the drawing code is
# moved to row_taker.gui.widgets.
_centered_text_position = centered_text_position


def _seat_kind_label(seat: LobbySeatView, *, is_self: bool) -> str:
    if is_self:
        return "Du"
    if seat.occupant_kind == ParticipantKind.BOT:
        return "Bot"
    if seat.occupant_kind == ParticipantKind.HUMAN:
        return "Mensch"
    return "frei"


def _seat_footer_text(seat: LobbySeatView, *, selected: bool) -> str:
    if selected:
        return "ausgewählt · Aktion unten wählen"
    if seat.occupant_display_name is None:
        return "bereit für Mensch oder Bot"
    return "belegt"


def _seat_fill_color(seat: LobbySeatView, *, is_self: bool) -> pygame.Color:
    if is_self:
        return PALETTE.seat_self
    if seat.occupant_kind == ParticipantKind.BOT:
        return PALETTE.seat_bot
    if seat.occupant_kind == ParticipantKind.HUMAN:
        return PALETTE.seat_human
    return PALETTE.seat_empty


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
        panel.left + 28,
        panel.top + 104,
        panel.width - 56,
        panel.height - 136,
    )
