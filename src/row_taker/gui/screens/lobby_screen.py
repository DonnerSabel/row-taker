from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.actions import (
    ClientActionAssignSelfToSeat,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionStartGame,
)
from row_taker.client.state import ClientState, enter_lobby_submenu, with_navigation_updates
from row_taker.gui.assets import DEFAULT_GUI_ASSETS
from row_taker.gui.lobby_layout import (
    DEFAULT_LOBBY_LAYOUT,
    BotNameDialogLayout,
    bottom_bar_inner_rect,
    compute_bot_name_dialog_layout,
    compute_lobby_panel_layout,
)
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_button, draw_overlay_panel, draw_panel, draw_vertical_gradient
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import PrimitiveDrawer
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import LobbySeatView

THEME = DEFAULT_THEME
PALETTE = THEME.palette
LAYOUT = DEFAULT_LOBBY_LAYOUT


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
    bot_name_input_rect: pygame.Rect | None = None
    bot_name_button_targets: tuple[LobbyButtonTarget, ...] = ()


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
    bot_dialog = compute_bot_name_dialog_layout(layout) if _is_editing_bot_name(state) else None
    return LobbyScreenTargets(
        seat_targets=_build_lobby_seat_targets(layout, state),
        button_targets=_build_lobby_button_targets(layout, state),
        bot_name_input_rect=None if bot_dialog is None else bot_dialog.input_rect,
        bot_name_button_targets=() if bot_dialog is None else _build_bot_name_button_targets(bot_dialog),
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
        if state is not None and _is_editing_bot_name(state):
            return ScreenResult(next_state=_leave_bot_name_editor(state))
        return ScreenResult(request_quit=True)
    if state is None or lobby_targets is None:
        return NO_SCREEN_RESULT
    if _is_editing_bot_name(state):
        return _handle_bot_name_event(event, state=state, lobby_targets=lobby_targets)
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
    if _is_editing_bot_name(client_state):
        _draw_bot_name_dialog(screen, drawer, layout, client_state, lobby_targets)


def _handle_left_click(
    position: tuple[int, int],
    *,
    state: ClientState,
    lobby_targets: LobbyScreenTargets,
) -> ScreenResult:
    for target in lobby_targets.seat_targets:
        if target.rect.collidepoint(position):
            seat = _seat_by_index(state, target.seat_index)
            if seat is not None and seat.occupant_kind == ParticipantKind.BOT:
                return ScreenResult(next_state=_enter_bot_name_editor(state, target.seat_index, seat.occupant_display_name))
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
        seat = _seat_by_index(state, selected_seat_index)
        initial_name = None if seat is None else seat.occupant_display_name
        return ScreenResult(next_state=_enter_bot_name_editor(state, selected_seat_index, initial_name))
    if button_id == "clear_seat":
        return ScreenResult(client_action=ClientActionClearSeat(seat_index=selected_seat_index))
    return NO_SCREEN_RESULT


def _handle_bot_name_event(
    event: pygame.event.Event,
    *,
    state: ClientState,
    lobby_targets: LobbyScreenTargets,
) -> ScreenResult:
    if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
        return NO_SCREEN_RESULT
    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return _confirm_bot_name(state)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
        return ScreenResult(next_state=_backspace_bot_name(state))
    if event.type == pygame.KEYDOWN and event.unicode:
        return ScreenResult(next_state=_append_bot_name_character(state, event.unicode))
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        for target in lobby_targets.bot_name_button_targets:
            if not target.rect.collidepoint(event.pos):
                continue
            if target.button_id == "confirm_bot_name":
                return _confirm_bot_name(state)
            if target.button_id == "cancel_bot_name":
                return ScreenResult(next_state=_leave_bot_name_editor(state))
    return NO_SCREEN_RESULT


def _build_lobby_seat_targets(layout: DemoLayout, state: ClientState) -> tuple[SeatTarget, ...]:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return ()

    panel_layout = compute_lobby_panel_layout(layout, lobby_view.seat_count)
    board_rect = panel_layout.seat_board_rect
    row_height = LAYOUT.seat_row_height
    gap = LAYOUT.seat_row_gap

    targets: list[SeatTarget] = []
    for index, seat in enumerate(lobby_view.seats):
        y = board_rect.top + index * (row_height + gap)
        targets.append(
            SeatTarget(
                seat_index=seat.seat_index,
                rect=pygame.Rect(board_rect.left, y, board_rect.width, row_height),
            )
        )
    return tuple(targets)


def _build_lobby_button_targets(layout: DemoLayout, state: ClientState) -> tuple[LobbyButtonTarget, ...]:
    bar = bottom_bar_inner_rect(layout)
    button_width = LAYOUT.action_button_width
    button_height = LAYOUT.action_button_height
    gap = LAYOUT.action_button_gap
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


def _build_bot_name_button_targets(dialog: BotNameDialogLayout) -> tuple[LobbyButtonTarget, ...]:
    return (
        LobbyButtonTarget("confirm_bot_name", "Übernehmen", dialog.confirm_button_rect),
        LobbyButtonTarget("cancel_bot_name", "Abbrechen", dialog.cancel_button_rect),
    )


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
    lobby_view = state.lobby_view
    seat_count = 4 if lobby_view is None else max(1, lobby_view.seat_count)
    panel_rect = compute_lobby_panel_layout(layout, seat_count).seats_rect
    draw_panel(
        screen,
        panel_rect,
        radius=THEME.spacing.large_panel_radius,
        fill=PALETTE.panel_fill_strong,
        border=PALETTE.panel_border_soft,
        alpha=168,
        theme=THEME,
    )
    drawer.draw_text(screen, "Sitzplätze", (panel_rect.left + 22, panel_rect.top + 18), role="title")

    if lobby_view is None:
        drawer.draw_text(screen, "Noch keine Lobby-Daten empfangen.", (panel_rect.left + 22, panel_rect.top + 70))
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
    fill_with_alpha = pygame.Color(fill)
    fill_with_alpha.a = 196 if selected or hovered else 142
    pygame.draw.rect(card_surface, fill_with_alpha, card_surface.get_rect(), border_radius=12)
    screen.blit(card_surface, rect)

    border = _seat_border_color(seat, selected=selected, hovered=hovered, is_self=is_self)
    pygame.draw.rect(screen, border, rect, width=2 if selected or hovered else 1, border_radius=12)

    baseline_y = rect.top + rect.height // 2
    number_text = f"{seat.seat_index + 1}."
    drawer.draw_text(screen, number_text, (rect.left + 12, baseline_y - 11), role="small", color=PALETTE.text_muted)

    icon_size = 20
    icon_rect = pygame.Rect(rect.left + 44, baseline_y - icon_size // 2, icon_size, icon_size)
    _draw_seat_icon(screen, icon_rect, seat=seat, is_self=is_self)

    occupant = seat.occupant_display_name or "frei"
    name_color = PALETTE.text_primary if not is_empty else PALETTE.text_muted
    drawer.draw_text(screen, occupant, (rect.left + 76, baseline_y - 12), role="body", color=name_color)

    if selected:
        _draw_selected_marker(screen, rect)


def _draw_seat_icon(screen: pygame.Surface, rect: pygame.Rect, *, seat: LobbySeatView, is_self: bool) -> None:
    center = rect.center
    if seat.occupant_display_name is None:
        color = PALETTE.panel_border_active
        pygame.draw.circle(screen, pygame.Color(color.r, color.g, color.b, 42), center, 8)
        pygame.draw.circle(screen, color, center, 7, width=2)
        pygame.draw.line(screen, color, (center[0] - 4, center[1]), (center[0] + 4, center[1]), width=2)
        pygame.draw.line(screen, color, (center[0], center[1] - 4), (center[0], center[1] + 4), width=2)
        return

    if seat.occupant_kind == ParticipantKind.BOT:
        color = PALETTE.gold
        head = pygame.Rect(rect.left + 2, rect.top + 3, rect.width - 4, rect.height - 6)
        pygame.draw.rect(screen, pygame.Color(color.r, color.g, color.b, 52), head, border_radius=5)
        pygame.draw.rect(screen, color, head, width=2, border_radius=5)
        pygame.draw.circle(screen, color, (head.left + 5, head.top + 6), 2)
        pygame.draw.circle(screen, color, (head.right - 5, head.top + 6), 2)
        pygame.draw.line(screen, color, (head.left + 5, head.bottom - 5), (head.right - 5, head.bottom - 5), width=2)
        return

    color = PALETTE.green if is_self else PALETTE.accent_hover
    pygame.draw.circle(screen, pygame.Color(color.r, color.g, color.b, 46), (center[0], center[1] - 4), 5)
    pygame.draw.circle(screen, color, (center[0], center[1] - 4), 5, width=2)
    body_rect = pygame.Rect(center[0] - 8, center[1] + 2, 16, 10)
    pygame.draw.rect(screen, pygame.Color(color.r, color.g, color.b, 46), body_rect, border_radius=6)
    pygame.draw.rect(screen, color, body_rect, width=2, border_radius=6)


def _draw_selected_marker(screen: pygame.Surface, rect: pygame.Rect) -> None:
    marker = pygame.Rect(rect.left, rect.top + 7, 4, rect.height - 14)
    pygame.draw.rect(screen, PALETTE.accent_hover, marker, border_radius=3)


def _draw_participants_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
) -> None:
    lobby_view = state.lobby_view
    seat_count = 4 if lobby_view is None else max(1, lobby_view.seat_count)
    rect = compute_lobby_panel_layout(layout, seat_count).participants_rect
    draw_panel(
        screen,
        rect,
        radius=THEME.spacing.large_panel_radius,
        fill=PALETTE.panel_fill_strong,
        border=PALETTE.panel_border_soft,
        alpha=174,
        theme=THEME,
    )
    content_left = rect.left + 18
    content_width = rect.width - 36
    y = rect.top + 18
    drawer.draw_text(screen, "Teilnehmer", (content_left, y), role="title")
    y += 40

    if lobby_view is None:
        drawer.draw_text(screen, "Keine Daten", (content_left, y), role="body", color=PALETTE.text_muted)
        return

    participants = tuple(
        participant
        for participant in lobby_view.participants
        if participant.participant_kind != ParticipantKind.BOT
    )
    if not participants:
        drawer.draw_text(screen, "Noch leer", (content_left, y), role="body", color=PALETTE.text_muted)
        return

    item_height = 46
    gap = 8
    visible_area_bottom = rect.bottom - 18
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
        radius=12,
        fill=fill,
        border=PALETTE.panel_border_active if is_self else PALETTE.panel_border_soft,
        alpha=160,
        theme=THEME,
    )

    icon_rect = pygame.Rect(rect.left + 10, rect.top + 9, 24, 24)
    _draw_participant_icon(screen, icon_rect, kind=participant.participant_kind, highlighted=is_self)
    color = PALETTE.green if is_self else PALETTE.text_primary
    drawer.draw_text(screen, participant.display_name, (rect.left + 42, rect.top + 8), role="body", color=color)

    seat_label = "-" if participant.seat_index is None else f"{participant.seat_index + 1}."
    drawer.draw_text(screen, f"Sitz {seat_label}", (rect.left + 42, rect.top + 27), role="tiny", color=PALETTE.text_muted)


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
    pygame.draw.circle(screen, pygame.Color(color.r, color.g, color.b, 42), (center[0], center[1] - 4), 5)
    pygame.draw.circle(screen, color, (center[0], center[1] - 4), 5, width=2)
    body_rect = pygame.Rect(center[0] - 8, center[1] + 2, 16, 10)
    pygame.draw.rect(screen, pygame.Color(color.r, color.g, color.b, 42), body_rect, border_radius=6)
    pygame.draw.rect(screen, color, body_rect, width=2, border_radius=6)


def _draw_participants_scroll_hint(screen: pygame.Surface, rect: pygame.Rect, *, total: int, visible: int) -> None:
    track = pygame.Rect(rect.right - 9, rect.top + 62, 3, rect.height - 82)
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
    rect = layout.footer_rect.inflate(-4, -14)
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
    if _is_editing_bot_name(state):
        return "Bot-Namen eingeben · Enter übernimmt · Esc bricht ab"
    selected = state.navigation_state.selected_seat_index
    if selected is None:
        return "Wähle einen Sitzplatz. Freie Plätze können belegt oder mit einem Bot vorbereitet werden."
    return f"{selected + 1}. ausgewählt · Aktion unten wählen"


def _draw_button(screen: pygame.Surface, drawer: PrimitiveDrawer, target: LobbyButtonTarget, *, hovered: bool) -> None:
    variant = "success" if target.button_id == "start_game" else "danger" if target.button_id == "clear_seat" else "primary"
    draw_button(screen, drawer, target.rect, target.label, variant=variant, hovered=hovered, theme=THEME)


def _draw_bot_name_dialog(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    targets: LobbyScreenTargets,
) -> None:
    dialog = compute_bot_name_dialog_layout(layout)
    shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    shade.fill(pygame.Color(0, 0, 0, 82))
    screen.blit(shade, (0, 0))

    draw_panel(
        screen,
        dialog.dialog_rect,
        radius=THEME.spacing.large_panel_radius,
        fill=PALETTE.panel_fill_strong,
        border=PALETTE.panel_border_active,
        alpha=236,
        theme=THEME,
    )
    seat_index = state.navigation_state.selected_seat_index
    seat_label = "?" if seat_index is None else f"{seat_index + 1}."
    drawer.draw_text(screen, "Bot benennen", (dialog.dialog_rect.left + 32, dialog.dialog_rect.top + 24), role="title")
    drawer.draw_text(
        screen,
        f"Name für Sitz {seat_label}",
        (dialog.dialog_rect.left + 32, dialog.dialog_rect.top + 58),
        role="body",
        color=PALETTE.text_muted,
    )
    _draw_bot_name_input(screen, drawer, dialog.input_rect, state)

    mouse_pos = pygame.mouse.get_pos()
    for target in targets.bot_name_button_targets:
        hovered = target.rect.collidepoint(mouse_pos)
        variant = "success" if target.button_id == "confirm_bot_name" else "neutral"
        draw_button(screen, drawer, target.rect, target.label, variant=variant, hovered=hovered, theme=THEME)


def _draw_bot_name_input(screen: pygame.Surface, drawer: PrimitiveDrawer, rect: pygame.Rect, state: ClientState) -> None:
    text = state.navigation_state.bot_name_text
    pygame.draw.rect(screen, PALETTE.panel_fill, rect, border_radius=14)
    pygame.draw.rect(screen, PALETTE.accent_hover, rect, width=2, border_radius=14)

    if state.navigation_state.bot_name_selected and text:
        font = drawer._font_for_role("body")
        text_width, text_height = font.size(text)
        selection_rect = pygame.Rect(rect.left + 12, rect.top + 8, text_width + 10, max(30, text_height + 8))
        selection_surface = pygame.Surface(selection_rect.size, pygame.SRCALPHA)
        selection_surface.fill(pygame.Color(80, 132, 212, 120))
        screen.blit(selection_surface, selection_rect)

    display_text = text or _default_bot_name(state)
    color = PALETTE.text_primary if text else PALETTE.text_muted
    drawer.draw_text(screen, display_text, (rect.left + 16, rect.top + 13), role="body", color=color)

    if not state.navigation_state.bot_name_selected:
        font = drawer._font_for_role("body")
        text_width = font.size(display_text)[0]
        cursor_x = min(rect.right - 16, rect.left + 16 + text_width + 2)
        pygame.draw.rect(screen, PALETTE.accent_hover, pygame.Rect(cursor_x, rect.top + 10, 2, rect.height - 20))


def _seat_border_color(seat: LobbySeatView, *, selected: bool, hovered: bool, is_self: bool) -> pygame.Color:
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


def _is_editing_bot_name(state: ClientState) -> bool:
    return state.navigation_state.lobby_submenu == "bot_name"


def _enter_bot_name_editor(state: ClientState, seat_index: int, initial_name: str | None) -> ClientState:
    next_state = enter_lobby_submenu(state, "bot_name", selected_seat_index=seat_index)
    return with_navigation_updates(
        next_state,
        bot_name_text=initial_name or _default_bot_name_for_seat(seat_index),
        bot_name_selected=True,
    )


def _leave_bot_name_editor(state: ClientState) -> ClientState:
    selected = state.navigation_state.selected_seat_index
    return with_navigation_updates(
        enter_lobby_submenu(state, "seat_edit", selected_seat_index=selected),
        bot_name_text="",
        bot_name_selected=False,
    )


def _append_bot_name_character(state: ClientState, character: str) -> ClientState:
    if len(character) != 1 or not character.isprintable():
        return state
    current = state.navigation_state.bot_name_text
    next_text = character if state.navigation_state.bot_name_selected else current + character
    if len(next_text) > 32:
        return state
    return with_navigation_updates(state, bot_name_text=next_text, bot_name_selected=False)


def _backspace_bot_name(state: ClientState) -> ClientState:
    current = state.navigation_state.bot_name_text
    next_text = "" if state.navigation_state.bot_name_selected else current[:-1]
    return with_navigation_updates(state, bot_name_text=next_text, bot_name_selected=False)


def _confirm_bot_name(state: ClientState) -> ScreenResult:
    seat_index = state.navigation_state.selected_seat_index
    if seat_index is None:
        return ScreenResult(next_state=enter_lobby_submenu(state, "main"))
    name = state.navigation_state.bot_name_text.strip() or _default_bot_name_for_seat(seat_index)
    return ScreenResult(client_action=ClientActionCreateBot(seat_index=seat_index, name=name))


def _default_bot_name(state: ClientState) -> str:
    seat_index = state.navigation_state.selected_seat_index
    return "Bot" if seat_index is None else _default_bot_name_for_seat(seat_index)


def _default_bot_name_for_seat(seat_index: int) -> str:
    return f"Bot_{seat_index + 1}"


def _seat_by_index(state: ClientState, seat_index: int) -> LobbySeatView | None:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return None
    for seat in lobby_view.seats:
        if seat.seat_index == seat_index:
            return seat
    return None


__all__ = [
    "LobbyButtonTarget",
    "LobbyScreen",
    "LobbyScreenTargets",
    "SeatTarget",
    "build_lobby_screen_targets",
    "handle_lobby_event",
    "render_lobby_screen",
]
