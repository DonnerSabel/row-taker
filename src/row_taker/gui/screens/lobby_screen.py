from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.actions import (
    ClientActionAssignSelfToSeat,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionStartGame,
)
from row_taker.client.state import (
    ClientState,
    UiMessage,
    enter_lobby_submenu,
    with_feedback_updates,
    with_navigation_updates,
)
from row_taker.gui.menu_layout import DEFAULT_MENU_LAYOUT, compute_lobby_panel_layout, row_rects
from row_taker.gui.menu_shell import (
    draw_menu_background,
    draw_menu_footer,
    draw_menu_header,
    draw_menu_panel,
    draw_text_input,
)
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_button, draw_panel
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import PrimitiveDrawer
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import LobbySeatView

THEME = DEFAULT_THEME
PALETTE = THEME.palette
MENU_LAYOUT = DEFAULT_MENU_LAYOUT


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
    seat_targets = _build_lobby_seat_targets(layout, state)
    edited_seat_index = state.navigation_state.selected_seat_index if _is_editing_bot_name(state) else None
    input_rect = next((target.rect.inflate(-72, -8).move(58, 0) for target in seat_targets if target.seat_index == edited_seat_index), None)
    return LobbyScreenTargets(
        seat_targets=seat_targets,
        button_targets=_build_lobby_button_targets(layout, state),
        bot_name_input_rect=input_rect,
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
    draw_menu_background(screen)
    lobby_view = client_state.lobby_view
    endpoint = "-" if lobby_view is None else lobby_view.server_endpoint or "-"
    draw_menu_header(screen, drawer, layout, title="Row-Taker Lobby", subtitle=f"Server: {endpoint}")
    _draw_lobby_panels(screen, drawer, layout, client_state, lobby_targets)
    hint, is_error = _footer_hint_text(client_state, lobby_targets)
    draw_menu_footer(screen, drawer, layout, text=hint, is_error=is_error)


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
            return ScreenResult(next_state=enter_lobby_submenu(state, "seat_edit", selected_seat_index=target.seat_index))

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
        return _confirm_bot_name(state)
    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return _confirm_bot_name(state)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
        return ScreenResult(next_state=_backspace_bot_name(state))
    if event.type == pygame.KEYDOWN and event.unicode:
        return ScreenResult(next_state=_append_bot_name_character(state, event.unicode))
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if lobby_targets.bot_name_input_rect is not None and lobby_targets.bot_name_input_rect.collidepoint(event.pos):
            return ScreenResult(next_state=with_navigation_updates(state, bot_name_selected=True))
        return _confirm_bot_name(state)
    return NO_SCREEN_RESULT


def _build_lobby_seat_targets(layout: DemoLayout, state: ClientState) -> tuple[SeatTarget, ...]:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return ()

    panel_layout = compute_lobby_panel_layout(layout, lobby_view.seat_count)
    rows = row_rects(panel_layout.seat_list_rect, len(lobby_view.seats))
    return tuple(
        SeatTarget(seat_index=seat.seat_index, rect=rows[index])
        for index, seat in enumerate(lobby_view.seats)
        if index < len(rows)
    )


def _build_lobby_button_targets(layout: DemoLayout, state: ClientState) -> tuple[LobbyButtonTarget, ...]:
    lobby_view = state.lobby_view
    seat_count = 4 if lobby_view is None else max(1, lobby_view.seat_count)
    action_rect = compute_lobby_panel_layout(layout, seat_count).action_rect
    button_width = MENU_LAYOUT.panel_button_secondary_width
    gap = MENU_LAYOUT.button_gap
    y = action_rect.top

    buttons: list[LobbyButtonTarget] = []
    x = action_rect.left
    selected_seat_index = state.navigation_state.selected_seat_index
    selected_seat = None if selected_seat_index is None else _seat_by_index(state, selected_seat_index)

    if selected_seat_index is not None:
        if selected_seat is None or selected_seat.occupant_display_name is None:
            for button_id, label in (("take_seat", "Nehmen"), ("create_bot", "Bot")):
                buttons.append(LobbyButtonTarget(button_id, label, pygame.Rect(x, y, button_width, MENU_LAYOUT.control_height)))
                x += button_width + gap
        elif selected_seat.occupant_kind == ParticipantKind.BOT:
            for button_id, label in (("create_bot", "Name"), ("clear_seat", "Leeren")):
                buttons.append(LobbyButtonTarget(button_id, label, pygame.Rect(x, y, button_width, MENU_LAYOUT.control_height)))
                x += button_width + gap
        else:
            buttons.append(LobbyButtonTarget("clear_seat", "Leeren", pygame.Rect(x, y, button_width, MENU_LAYOUT.control_height)))
            x += button_width + gap

        buttons.append(LobbyButtonTarget("back", "Lösen", pygame.Rect(x, y, button_width, MENU_LAYOUT.control_height)))

    start_width = MENU_LAYOUT.panel_button_width
    buttons.append(
        LobbyButtonTarget(
            button_id="start_game",
            label="Spiel starten",
            rect=pygame.Rect(action_rect.right - start_width, y, start_width, MENU_LAYOUT.control_height),
        )
    )
    return tuple(buttons)


def _draw_lobby_panels(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    state: ClientState,
    targets: LobbyScreenTargets,
) -> None:
    lobby_view = state.lobby_view
    seat_count = 4 if lobby_view is None else max(1, lobby_view.seat_count)
    panel_layout = compute_lobby_panel_layout(layout, seat_count)

    _draw_seat_area(screen, drawer, panel_layout.seats_rect, state, targets)
    _draw_participants_panel(screen, drawer, panel_layout.participants_rect, state)


def _draw_seat_area(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    panel_rect: pygame.Rect,
    state: ClientState,
    targets: LobbyScreenTargets,
) -> None:
    lobby_view = state.lobby_view
    draw_menu_panel(screen, panel_rect, alpha=168)
    drawer.draw_text(screen, "Sitzplätze", (panel_rect.left + MENU_LAYOUT.panel_padding_x, panel_rect.top + 20), role="title")

    if lobby_view is None:
        drawer.draw_text(screen, "Noch keine Lobby-Daten empfangen.", (panel_rect.left + MENU_LAYOUT.panel_padding_x, panel_rect.top + 76))
        return

    mouse_pos = pygame.mouse.get_pos()
    seats_by_index = {seat.seat_index: seat for seat in lobby_view.seats}
    for target in targets.seat_targets:
        seat = seats_by_index[target.seat_index]
        selected = state.navigation_state.selected_seat_index == target.seat_index
        hovered = target.rect.collidepoint(mouse_pos)
        editing = _is_editing_bot_name(state) and selected
        _draw_seat_card(screen, drawer, target.rect, seat, state, selected=selected, hovered=hovered, editing=editing)

    _draw_action_buttons(screen, drawer, targets)


def _draw_action_buttons(screen: pygame.Surface, drawer: PrimitiveDrawer, targets: LobbyScreenTargets) -> None:
    mouse_pos = pygame.mouse.get_pos()
    for target in targets.button_targets:
        hovered = target.rect.collidepoint(mouse_pos)
        variant = "success" if target.button_id == "start_game" else "neutral"
        if target.button_id == "create_bot":
            variant = "primary"
        draw_button(screen, drawer, target.rect, target.label, variant=variant, hovered=hovered, theme=THEME)


def _draw_seat_card(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    seat: LobbySeatView,
    state: ClientState,
    *,
    selected: bool,
    hovered: bool,
    editing: bool,
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
    drawer.draw_text(screen, f"{seat.seat_index + 1}.", (rect.left + 12, baseline_y - 11), role="small", color=PALETTE.text_muted)

    icon_size = 20
    icon_rect = pygame.Rect(rect.left + 44, baseline_y - icon_size // 2, icon_size, icon_size)
    _draw_seat_icon(screen, icon_rect, seat=seat, is_self=is_self)

    if editing:
        input_rect = rect.inflate(-72, -8).move(58, 0)
        draw_text_input(
            screen,
            drawer,
            input_rect,
            value=state.navigation_state.bot_name_text,
            placeholder=_default_bot_name(state),
            active=True,
            hovered=True,
            selected=state.navigation_state.bot_name_selected,
        )
    else:
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
    rect: pygame.Rect,
    state: ClientState,
) -> None:
    lobby_view = state.lobby_view
    draw_menu_panel(screen, rect, alpha=174)
    content_left = rect.left + 18
    content_width = rect.width - 36
    y = rect.top + 20
    drawer.draw_text(screen, "Teilnehmer", (content_left, y), role="title")
    y += 58

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

    visible_area_bottom = rect.bottom - 18
    max_visible = max(1, (visible_area_bottom - y + MENU_LAYOUT.control_gap) // (MENU_LAYOUT.control_height + MENU_LAYOUT.control_gap))
    for participant in participants[:max_visible]:
        participant_rect = pygame.Rect(content_left, y, content_width, MENU_LAYOUT.control_height)
        _draw_participant_card(screen, drawer, participant_rect, participant, own_client_id=state.own_client_id)
        y += MENU_LAYOUT.control_height + MENU_LAYOUT.control_gap

    if len(participants) > max_visible:
        _draw_participants_scroll_hint(screen, rect, total=len(participants), visible=max_visible)


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
        radius=10,
        fill=fill,
        border=PALETTE.green if is_self else PALETTE.panel_border,
        alpha=180,
        theme=THEME,
    )
    icon_rect = pygame.Rect(rect.left + 14, rect.top + 17, 20, 20)
    _draw_participant_icon(screen, icon_rect, is_self=is_self)
    name_color = PALETTE.green if is_self else PALETTE.text_primary
    drawer.draw_text(screen, participant.display_name, (rect.left + 44, rect.top + 9), role="body", color=name_color)
    seat_text = "Sitz -" if participant.seat_index is None else f"Sitz {participant.seat_index + 1}"
    drawer.draw_text(screen, seat_text, (rect.left + 44, rect.top + 31), role="small", color=PALETTE.text_muted)


def _draw_participant_icon(screen: pygame.Surface, rect: pygame.Rect, *, is_self: bool) -> None:
    color = PALETTE.green if is_self else PALETTE.accent_hover
    center = rect.center
    pygame.draw.circle(screen, color, (center[0], center[1] - 4), 4)
    pygame.draw.rect(screen, color, pygame.Rect(center[0] - 7, center[1] + 2, 14, 9), border_radius=6)


def _draw_participants_scroll_hint(screen: pygame.Surface, rect: pygame.Rect, *, total: int, visible: int) -> None:
    track = pygame.Rect(rect.right - 10, rect.top + 76, 4, max(20, rect.height - 96))
    pygame.draw.rect(screen, pygame.Color(255, 255, 255, 36), track, border_radius=3)
    fraction = max(0.1, visible / total)
    thumb_height = max(18, int(track.height * fraction))
    pygame.draw.rect(screen, PALETTE.panel_border_active, pygame.Rect(track.left, track.top, track.width, thumb_height), border_radius=3)


def _footer_hint_text(state: ClientState, targets: LobbyScreenTargets) -> tuple[str, bool]:
    if state.flash_message is not None:
        return state.flash_message.text, state.flash_message.level == "error"
    if _is_editing_bot_name(state):
        return "Botname eingeben · Enter oder Klick außerhalb übernimmt · Esc bricht ab", False

    hovered = _hovered_button_id(targets)
    if hovered == "start_game":
        return "Spiel mit der aktuellen Sitzplatzbelegung starten.", False
    if hovered == "take_seat":
        return "Ausgewählten Sitzplatz selbst belegen.", False
    if hovered == "create_bot":
        return "Botnamen direkt im ausgewählten Sitzplatz eingeben.", False
    if hovered == "clear_seat":
        return "Ausgewählten Sitzplatz wieder freigeben.", False

    selected = state.navigation_state.selected_seat_index
    if selected is not None:
        return f"Sitz {selected + 1} ausgewählt. Wähle eine Aktion unten im Sitzplätze-Fenster.", False
    return "Wähle einen Sitzplatz. Freie Plätze können belegt oder mit einem Bot vorbereitet werden.", False


def _hovered_button_id(targets: LobbyScreenTargets) -> str | None:
    mouse_pos = pygame.mouse.get_pos()
    for target in targets.button_targets:
        if target.rect.collidepoint(mouse_pos):
            return target.button_id
    return None


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
    next_state = with_feedback_updates(next_state, flash_message=None)
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
    next_state = with_feedback_updates(state, flash_message=None)
    return with_navigation_updates(next_state, bot_name_text=next_text, bot_name_selected=False)


def _backspace_bot_name(state: ClientState) -> ClientState:
    current = state.navigation_state.bot_name_text
    next_text = "" if state.navigation_state.bot_name_selected else current[:-1]
    next_state = with_feedback_updates(state, flash_message=None)
    return with_navigation_updates(next_state, bot_name_text=next_text, bot_name_selected=False)


def _confirm_bot_name(state: ClientState) -> ScreenResult:
    seat_index = state.navigation_state.selected_seat_index
    if seat_index is None:
        return ScreenResult(next_state=enter_lobby_submenu(state, "main"))
    name = state.navigation_state.bot_name_text.strip() or _default_bot_name_for_seat(seat_index)
    collision = _bot_name_collision(state, name=name, edited_seat_index=seat_index)
    if collision is not None:
        return ScreenResult(
            next_state=with_feedback_updates(
                state,
                flash_message=UiMessage(level="error", text=f"Name bereits vergeben: {collision}"),
            )
        )
    return ScreenResult(client_action=ClientActionCreateBot(seat_index=seat_index, name=name))


def _bot_name_collision(state: ClientState, *, name: str, edited_seat_index: int) -> str | None:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return None
    normalized = name.casefold()
    for participant in lobby_view.participants:
        if participant.seat_index == edited_seat_index:
            continue
        if participant.display_name.casefold() == normalized:
            return participant.display_name
    for seat in lobby_view.seats:
        if seat.seat_index == edited_seat_index or seat.occupant_display_name is None:
            continue
        if seat.occupant_display_name.casefold() == normalized:
            return seat.occupant_display_name
    return None


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
