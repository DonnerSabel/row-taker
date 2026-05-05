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
from row_taker.gui_common.primitives import TEXT_MUTED, WINDOW_BACKGROUND, PrimitiveDrawer
from row_taker.gui_common.ui.common_render import (
    format_presentation_event,
    render_standard_footer,
    render_standard_header,
)
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult


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
        return handle_lobby_event(
            event,
            state=self.state,
            lobby_targets=targets,
        )

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
    screen.fill(WINDOW_BACKGROUND)
    render_standard_header(screen, drawer, layout, client_state)
    _render_lobby_panels(screen, drawer, layout, client_state, lobby_targets)
    _render_sidebar(screen, drawer, layout, client_state, frame_count, last_action_summary)
    render_standard_footer(screen, drawer, layout)


def _handle_left_click(
    position: tuple[int, int],
    *,
    state: ClientState,
    lobby_targets: LobbyScreenTargets,
) -> ScreenResult:
    for target in lobby_targets.seat_targets:
        if target.rect.collidepoint(position):
            next_state = enter_lobby_submenu(state, 'seat_edit', selected_seat_index=target.seat_index)
            return ScreenResult(next_state=next_state)

    for target in lobby_targets.button_targets:
        if target.rect.collidepoint(position):
            return _map_lobby_button(target.button_id, state)

    return NO_SCREEN_RESULT


def _map_lobby_button(button_id: str, state: ClientState) -> ScreenResult:
    seat_index = state.navigation_state.selected_seat_index
    if button_id == 'start_game':
        return ScreenResult(client_action=ClientActionStartGame())
    if button_id == 'back':
        return ScreenResult(next_state=enter_lobby_submenu(state, 'main'))
    if seat_index is None:
        return NO_SCREEN_RESULT
    if button_id == 'take_seat':
        return ScreenResult(client_action=ClientActionAssignSelfToSeat(seat_index=seat_index))
    if button_id == 'create_bot':
        return ScreenResult(client_action=ClientActionCreateBot(seat_index=seat_index, name=f'Bot_{seat_index + 1}'))
    if button_id == 'clear_seat':
        return ScreenResult(client_action=ClientActionClearSeat(seat_index=seat_index))
    return NO_SCREEN_RESULT


def _build_lobby_seat_targets(layout: DemoLayout, state: ClientState) -> tuple[SeatTarget, ...]:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return ()

    seat_targets: list[SeatTarget] = []
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
        seat_targets.append(SeatTarget(seat_index=seat.seat_index, rect=seat_rect))
    return tuple(seat_targets)


def _build_lobby_button_targets(layout: DemoLayout, state: ClientState) -> tuple[LobbyButtonTarget, ...]:
    top_rect = layout.main_top_rect.inflate(-24, -24)
    bottom_rect = layout.main_bottom_rect.inflate(-24, -24)
    selected_seat_index = state.navigation_state.selected_seat_index

    buttons: list[LobbyButtonTarget] = []

    if selected_seat_index is None:
        start_rect = pygame.Rect(top_rect.right - 170, top_rect.top + 28, 150, 34)
        buttons.append(LobbyButtonTarget(button_id='start_game', label='Spiel starten', rect=start_rect))
        return tuple(buttons)

    button_specs = [
        ('take_seat', 'Platz nehmen'),
        ('create_bot', 'Bot erzeugen'),
        ('clear_seat', 'Platz leeren'),
        ('back', 'Zurück'),
        ('start_game', 'Spiel starten'),
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


def _render_lobby_panels(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    lobby_targets: LobbyScreenTargets,
) -> None:
    top_content = drawer.draw_panel(screen, layout.main_top_rect, title='Lobby-Plätze')
    bottom_content = drawer.draw_panel(screen, layout.main_bottom_rect, title='Teilnehmer / Befehle')

    lobby_view = client_state.lobby_view
    if lobby_view is None:
        drawer.draw_wrapped_lines(screen, ['Keine Lobby-Ansicht verfügbar.'], top_content)
        return

    drawer.draw_text(
        screen,
        f'Server-Endpunkt: {lobby_view.server_endpoint or "-"}',
        (top_content.left, top_content.top),
        role='small',
        color=TEXT_MUTED,
    )

    for target in lobby_targets.seat_targets:
        seat = lobby_view.seats[target.seat_index]
        occupant = seat.occupant_display_name or '-'
        label = f'Seat {seat.seat_index + 1}: {occupant}'
        if seat.occupant_kind is not None:
            label += f' [{seat.occupant_kind}]'
        active = client_state.navigation_state.selected_seat_index == seat.seat_index
        drawer.draw_badge(screen, target.rect, text=label, active=active)

    participant_lines: list[str] = []
    for participant in lobby_view.participants:
        seat_label = '-' if participant.seat_index is None else str(participant.seat_index + 1)
        participant_lines.append(
            f'{participant.display_name} [{participant.participant_kind}] seat={seat_label} endpoint={participant.endpoint or "-"}'
        )

    participant_text_rect = bottom_content.copy()
    participant_text_rect.height = max(60, bottom_content.height - 52)
    drawer.draw_wrapped_lines(screen, participant_lines, participant_text_rect, role='body')

    for target in lobby_targets.button_targets:
        active = target.button_id == 'start_game' or client_state.navigation_state.selected_seat_index is not None
        drawer.draw_badge(screen, target.rect, text=target.label, active=active)


def _render_sidebar(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    last_action_summary: str,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.sidebar_rect, title='Zustandsübersicht')
    y = content_rect.top

    entries = [
        ('client_mode', client_state.client_mode.value),
        ('pending_action', client_state.pending_action.value),
        ('own_client_id', client_state.own_client_id or '-'),
        ('own_player_id', client_state.own_player_id or '-'),
        ('lobby_submenu', client_state.navigation_state.lobby_submenu),
        ('session_error', client_state.session_error or '-'),
        ('presentation', str(len(client_state.pending_presentation_events))),
        ('frame', str(frame_count)),
    ]

    for key, value in entries:
        drawer.draw_key_value(screen, key, value, (content_rect.left, y))
        y += 28

    drawer.draw_text(screen, 'last_gui_action', (content_rect.left, y + 6), role='small', color=TEXT_MUTED)
    action_rect = content_rect.copy()
    action_rect.top = y + 28
    action_rect.height = 72
    drawer.draw_wrapped_lines(screen, [last_action_summary], action_rect, role='small')

    flash_text = client_state.flash_message.text if client_state.flash_message is not None else 'Keine Meldung'
    drawer.draw_text(screen, 'flash_message', (content_rect.left, action_rect.bottom + 10), role='small', color=TEXT_MUTED)
    flash_rect = content_rect.copy()
    flash_rect.top = action_rect.bottom + 32
    flash_rect.height = 64
    drawer.draw_wrapped_lines(screen, [flash_text], flash_rect, role='body')

    events_rect = content_rect.copy()
    events_rect.top = flash_rect.bottom + 18
    events_bottom = layout.sidebar_rect.bottom - 70
    events_rect.height = max(40, events_bottom - events_rect.top)
    drawer.draw_text(screen, 'presentation events', (events_rect.left, events_rect.top), role='small', color=TEXT_MUTED)
    events_rect.top += 22
    event_lines = [format_presentation_event(event) for event in client_state.pending_presentation_events]
    if not event_lines:
        event_lines = ['Keine ausstehenden Präsentationsereignisse.']
    drawer.draw_wrapped_lines(screen, event_lines, events_rect, role='small')

