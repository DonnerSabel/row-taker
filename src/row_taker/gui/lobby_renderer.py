from __future__ import annotations

import pygame

from row_taker.client.state import ClientState
from row_taker.gui.layout import GuiLayout
from row_taker.gui.lobby_interaction import (
    LobbyScreenTargets,
    default_bot_name,
    is_editing_bot_name,
)
from row_taker.gui.lobby_layout import compute_lobby_panel_layout
from row_taker.gui.menu_layout import DEFAULT_MENU_LAYOUT
from row_taker.gui.menu_shell import (
    draw_menu_background,
    draw_menu_footer,
    draw_menu_header,
    draw_menu_panel,
    draw_text_input,
)
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import ButtonVariant, draw_button, draw_panel
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import LobbyParticipantView, LobbySeatView

THEME = DEFAULT_THEME
PALETTE = THEME.palette
MENU_LAYOUT = DEFAULT_MENU_LAYOUT


def render_lobby_screen(
    screen: pygame.Surface,
    *,
    drawer: PrimitiveDrawer,
    layout: GuiLayout,
    client_state: ClientState,
    lobby_targets: LobbyScreenTargets,
    mouse_pos: tuple[int, int],
) -> None:
    draw_menu_background(screen)
    lobby_view = client_state.lobby_view
    endpoint = "-" if lobby_view is None else lobby_view.server_endpoint or "-"
    draw_menu_header(
        screen, drawer, layout, title="Row-Taker Lobby", subtitle=f"Server: {endpoint}"
    )
    _draw_lobby_panels(
        screen,
        drawer,
        layout,
        client_state,
        lobby_targets,
        mouse_pos=mouse_pos,
    )
    hint, is_error = _footer_hint_text(
        client_state,
        lobby_targets,
        mouse_pos=mouse_pos,
    )
    draw_menu_footer(screen, drawer, layout, text=hint, is_error=is_error)


def _draw_lobby_panels(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: GuiLayout,
    state: ClientState,
    targets: LobbyScreenTargets,
    *,
    mouse_pos: tuple[int, int],
) -> None:
    lobby_view = state.lobby_view
    seat_count = 4 if lobby_view is None else max(1, lobby_view.seat_count)
    panel_layout = compute_lobby_panel_layout(layout, seat_count)

    _draw_seat_area(
        screen,
        drawer,
        panel_layout.seats_rect,
        state,
        targets,
        mouse_pos=mouse_pos,
    )
    _draw_participants_panel(screen, drawer, panel_layout.participants_rect, state)


def _draw_seat_area(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    panel_rect: pygame.Rect,
    state: ClientState,
    targets: LobbyScreenTargets,
    *,
    mouse_pos: tuple[int, int],
) -> None:
    lobby_view = state.lobby_view
    draw_menu_panel(screen, panel_rect, alpha=168)
    drawer.draw_text(
        screen,
        "Sitzplätze",
        (panel_rect.left + MENU_LAYOUT.panel_padding_x, panel_rect.top + 20),
        role="title",
    )

    if lobby_view is None:
        drawer.draw_text(
            screen,
            "Noch keine Lobby-Daten empfangen.",
            (panel_rect.left + MENU_LAYOUT.panel_padding_x, panel_rect.top + 76),
        )
        return

    seats_by_index = {seat.seat_index: seat for seat in lobby_view.seats}
    for target in targets.seat_targets:
        seat = seats_by_index[target.seat_index]
        selected = state.navigation_state.selected_seat_index == target.seat_index
        hovered = target.rect.collidepoint(mouse_pos)
        editing = is_editing_bot_name(state) and selected
        _draw_seat_card(
            screen,
            drawer,
            target.rect,
            seat,
            state,
            selected=selected,
            hovered=hovered,
            editing=editing,
        )

    _draw_action_buttons(screen, drawer, targets, mouse_pos=mouse_pos)


def _draw_action_buttons(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    targets: LobbyScreenTargets,
    *,
    mouse_pos: tuple[int, int],
) -> None:
    for target in targets.button_targets:
        hovered = target.rect.collidepoint(mouse_pos)
        variant: ButtonVariant = "success" if target.button_id == "start_game" else "neutral"
        if target.button_id == "create_bot":
            variant = "primary"
        draw_button(
            screen, drawer, target.rect, target.label, variant=variant, hovered=hovered, theme=THEME
        )


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
    drawer.draw_text(
        screen,
        f"{seat.seat_index + 1}.",
        (rect.left + 12, baseline_y - 11),
        role="small",
        color=PALETTE.text_muted,
    )

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
            placeholder=default_bot_name(state),
            active=True,
            hovered=True,
            selected=state.navigation_state.bot_name_selected,
        )
    else:
        occupant = seat.occupant_display_name or "frei"
        name_color = PALETTE.text_primary if not is_empty else PALETTE.text_muted
        drawer.draw_text(
            screen, occupant, (rect.left + 76, baseline_y - 12), role="body", color=name_color
        )

    if selected:
        _draw_selected_marker(screen, rect)


def _draw_seat_icon(
    screen: pygame.Surface, rect: pygame.Rect, *, seat: LobbySeatView, is_self: bool
) -> None:
    center = rect.center
    if seat.occupant_display_name is None:
        color = PALETTE.panel_border_active
        pygame.draw.circle(screen, pygame.Color(color.r, color.g, color.b, 42), center, 8)
        pygame.draw.circle(screen, color, center, 7, width=2)
        pygame.draw.line(
            screen, color, (center[0] - 4, center[1]), (center[0] + 4, center[1]), width=2
        )
        pygame.draw.line(
            screen, color, (center[0], center[1] - 4), (center[0], center[1] + 4), width=2
        )
        return

    if seat.occupant_kind == ParticipantKind.BOT:
        color = PALETTE.gold
        head = pygame.Rect(rect.left + 2, rect.top + 3, rect.width - 4, rect.height - 6)
        pygame.draw.rect(screen, pygame.Color(color.r, color.g, color.b, 52), head, border_radius=5)
        pygame.draw.rect(screen, color, head, width=2, border_radius=5)
        pygame.draw.circle(screen, color, (head.left + 5, head.top + 6), 2)
        pygame.draw.circle(screen, color, (head.right - 5, head.top + 6), 2)
        pygame.draw.line(
            screen,
            color,
            (head.left + 5, head.bottom - 5),
            (head.right - 5, head.bottom - 5),
            width=2,
        )
        return

    color = PALETTE.green if is_self else PALETTE.accent_hover
    pygame.draw.circle(
        screen, pygame.Color(color.r, color.g, color.b, 46), (center[0], center[1] - 4), 5
    )
    pygame.draw.circle(screen, color, (center[0], center[1] - 4), 5, width=2)
    body_rect = pygame.Rect(center[0] - 8, center[1] + 2, 16, 10)
    pygame.draw.rect(
        screen, pygame.Color(color.r, color.g, color.b, 46), body_rect, border_radius=6
    )
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
        drawer.draw_text(
            screen, "Keine Daten", (content_left, y), role="body", color=PALETTE.text_muted
        )
        return

    participants = tuple(
        participant
        for participant in lobby_view.participants
        if participant.participant_kind != ParticipantKind.BOT
    )
    if not participants:
        drawer.draw_text(
            screen, "Noch leer", (content_left, y), role="body", color=PALETTE.text_muted
        )
        return

    visible_area_bottom = rect.bottom - 18
    max_visible = max(
        1,
        (visible_area_bottom - y + MENU_LAYOUT.control_gap)
        // (MENU_LAYOUT.control_height + MENU_LAYOUT.control_gap),
    )
    for participant in participants[:max_visible]:
        participant_rect = pygame.Rect(content_left, y, content_width, MENU_LAYOUT.control_height)
        _draw_participant_card(
            screen, drawer, participant_rect, participant, own_client_id=state.own_client_id
        )
        y += MENU_LAYOUT.control_height + MENU_LAYOUT.control_gap

    if len(participants) > max_visible:
        _draw_participants_scroll_hint(screen, rect, total=len(participants), visible=max_visible)


def _draw_participant_card(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    participant: LobbyParticipantView,
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
    drawer.draw_text(
        screen,
        participant.display_name,
        (rect.left + 44, rect.top + 9),
        role="body",
        color=name_color,
    )
    seat_text = "Sitz -" if participant.seat_index is None else f"Sitz {participant.seat_index + 1}"
    drawer.draw_text(
        screen, seat_text, (rect.left + 44, rect.top + 31), role="small", color=PALETTE.text_muted
    )


def _draw_participant_icon(screen: pygame.Surface, rect: pygame.Rect, *, is_self: bool) -> None:
    color = PALETTE.green if is_self else PALETTE.accent_hover
    center = rect.center
    pygame.draw.circle(screen, color, (center[0], center[1] - 4), 4)
    pygame.draw.rect(
        screen, color, pygame.Rect(center[0] - 7, center[1] + 2, 14, 9), border_radius=6
    )


def _draw_participants_scroll_hint(
    screen: pygame.Surface, rect: pygame.Rect, *, total: int, visible: int
) -> None:
    track = pygame.Rect(rect.right - 10, rect.top + 76, 4, max(20, rect.height - 96))
    pygame.draw.rect(screen, pygame.Color(255, 255, 255, 36), track, border_radius=3)
    fraction = max(0.1, visible / total)
    thumb_height = max(18, int(track.height * fraction))
    pygame.draw.rect(
        screen,
        PALETTE.panel_border_active,
        pygame.Rect(track.left, track.top, track.width, thumb_height),
        border_radius=3,
    )


def _footer_hint_text(
    state: ClientState,
    targets: LobbyScreenTargets,
    *,
    mouse_pos: tuple[int, int],
) -> tuple[str, bool]:
    if state.flash_message is not None:
        return state.flash_message.text, state.flash_message.level == "error"
    if is_editing_bot_name(state):
        return "Botname eingeben · Enter oder Klick außerhalb übernimmt · Esc bricht ab", False

    hovered = _hovered_button_id(targets, mouse_pos)
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
        return (
            f"Sitz {selected + 1} ausgewählt. Wähle eine Aktion unten im Sitzplätze-Fenster.",
            False,
        )
    return (
        "Wähle einen Sitzplatz. Freie Plätze können belegt oder mit einem Bot vorbereitet werden.",
        False,
    )


def _hovered_button_id(
    targets: LobbyScreenTargets,
    mouse_pos: tuple[int, int],
) -> str | None:
    for target in targets.button_targets:
        if target.rect.collidepoint(mouse_pos):
            return target.button_id
    return None


def _seat_border_color(
    seat: LobbySeatView, *, selected: bool, hovered: bool, is_self: bool
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


__all__ = ["render_lobby_screen"]
