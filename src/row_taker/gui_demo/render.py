from __future__ import annotations

import pygame

from row_taker.client.presentation_events import (
    PresentationCardsRevealed,
    PresentationEvent,
    PresentationOverflowResolved,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
    PresentationTrickFinished,
)
from row_taker.client.state import ClientState
from row_taker.participants import ParticipantKind
from row_taker.engine.game import Phase
from row_taker.gui_demo.connect_screen import ConnectFormState, ConnectScreenTargets
from row_taker.gui_demo.layout import DemoLayout
from row_taker.gui_demo.primitives import (
    ACCENT,
    PANEL_BORDER,
    PANEL_FILL,
    TEXT_MUTED,
    WINDOW_BACKGROUND,
    PrimitiveDrawer,
)


def render_connect_screen(
    screen: pygame.Surface,
    *,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    connect_form: ConnectFormState,
    connect_targets: ConnectScreenTargets,
) -> None:
    screen.fill(WINDOW_BACKGROUND)

    header_content = drawer.draw_panel(screen, layout.header_rect)
    drawer.draw_text(screen, "Row-Taker GUI Demo", (header_content.left, header_content.top), role="title")
    drawer.draw_text(
        screen,
        "Einfach verbinden und dann direkt spielen.",
        (header_content.left, header_content.top + 34),
        role="small",
        color=TEXT_MUTED,
    )

    pygame.draw.rect(screen, PANEL_FILL, connect_targets.panel_rect)
    pygame.draw.rect(screen, PANEL_BORDER, connect_targets.panel_rect, width=1)

    title_pos = (connect_targets.panel_rect.left + 24, connect_targets.panel_rect.top + 18)
    drawer.draw_text(screen, "Connect", title_pos, role="title")

    for target in connect_targets.field_targets:
        active = connect_form.active_field == target.field_name
        value = getattr(connect_form, target.field_name)
        label_pos = (target.rect.left, target.rect.top - 18)
        drawer.draw_text(screen, target.label, label_pos, role="small", color=TEXT_MUTED)
        drawer.draw_badge(screen, target.rect, text=value or " ", active=active)

    for target in connect_targets.button_targets:
        drawer.draw_badge(screen, target.rect, text=target.label, active=(target.button_id == "connect"))

    status_rect = pygame.Rect(
        connect_targets.panel_rect.left + 24,
        connect_targets.panel_rect.bottom - 114,
        connect_targets.panel_rect.width - 48,
        20,
    )
    drawer.draw_text(screen, connect_form.status_message, (status_rect.left, status_rect.top), role="small", color=TEXT_MUTED)

    if connect_form.error_message is not None:
        error_rect = pygame.Rect(
            connect_targets.panel_rect.left + 24,
            connect_targets.panel_rect.bottom - 88,
            connect_targets.panel_rect.width - 48,
            44,
        )
        drawer.draw_wrapped_lines(screen, [connect_form.error_message], error_rect, role="small", color=ACCENT)

    footer_content = drawer.draw_panel(screen, layout.footer_rect)
    drawer.draw_wrapped_lines(
        screen,
        [
            "Tab nächstes Feld",
            "Enter connect",
            "ESC quit",
        ],
        footer_content,
        role="small",
        color=TEXT_MUTED,
    )


def render_session(
    screen,
    *,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    interaction_map: object,
    last_action_summary: str,
) -> None:
    screen.fill(WINDOW_BACKGROUND)
    _render_header(screen, drawer, layout, client_state)
    _render_main_area(screen, drawer, layout, client_state, interaction_map)
    _render_sidebar(screen, drawer, layout, client_state, frame_count, last_action_summary, interaction_map)
    _render_footer(screen, drawer, layout)


def _render_header(
    screen,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.header_rect)
    drawer.draw_text(screen, "Row-Taker GUI Demo", (content_rect.left, content_rect.top), role="title")
    subtitle = (
        "Einfaches pygame-Frontend auf dem gemeinsamen ClientState. "
        f"Mode={client_state.client_mode.value}, pending_action={client_state.pending_action.value}"
    )
    drawer.draw_text(
        screen,
        subtitle,
        (content_rect.left, content_rect.top + 34),
        role="small",
        color=TEXT_MUTED,
    )


def _render_main_area(
    screen,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    interaction_map: object,
) -> None:
    if client_state.client_mode.value == "lobby":
        _render_lobby_panels(screen, drawer, layout, client_state, interaction_map)
        return
    if client_state.public_state is not None or client_state.player_state is not None:
        _render_game_panels(screen, drawer, layout, client_state, interaction_map)
        return

    content_rect = drawer.draw_panel(screen, layout.main_rect, title="Current view")
    drawer.draw_wrapped_lines(screen, ["Noch keine Lobby- oder Spielansicht verfügbar."], content_rect)


def _render_lobby_panels(
    screen,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    interaction_map: object,
) -> None:
    top_content = drawer.draw_panel(screen, layout.main_top_rect, title="Lobby seats")
    bottom_content = drawer.draw_panel(screen, layout.main_bottom_rect, title="Participants / commands")

    lobby_view = client_state.lobby_view
    if lobby_view is None:
        drawer.draw_wrapped_lines(screen, ["No lobby view available."], top_content)
        return

    drawer.draw_text(
        screen,
        f"server_endpoint: {lobby_view.server_endpoint or '-'}",
        (top_content.left, top_content.top),
        role="small",
        color=TEXT_MUTED,
    )

    for target in interaction_map.seat_targets:
        seat = lobby_view.seats[target.seat_index]
        occupant = seat.occupant_display_name or "-"
        label = f"Seat {seat.seat_index + 1}: {occupant}"
        if seat.occupant_kind is not None:
            label += f" [{seat.occupant_kind}]"
        active = client_state.navigation_state.selected_seat_index == seat.seat_index
        drawer.draw_badge(screen, target.rect, text=label, active=active)

    participant_lines = []
    for participant in lobby_view.participants:
        seat_label = "-" if participant.seat_index is None else str(participant.seat_index + 1)
        participant_lines.append(
            f"{participant.display_name} [{participant.participant_kind}] seat={seat_label} endpoint={participant.endpoint or '-'}"
        )

    participant_text_rect = bottom_content.copy()
    participant_text_rect.height = max(60, bottom_content.height - 52)
    drawer.draw_wrapped_lines(screen, participant_lines, participant_text_rect, role="body")

    for target in interaction_map.lobby_button_targets:
        active = target.button_id == "start_game" or client_state.navigation_state.selected_seat_index is not None
        drawer.draw_badge(screen, target.rect, text=target.label, active=active)


def _render_game_panels(
    screen,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    interaction_map: object,
) -> None:
    top_content = drawer.draw_panel(screen, layout.main_top_rect, title="Rows and players")
    bottom_content = drawer.draw_panel(screen, layout.main_bottom_rect, title="Own hand")

    _render_rows_and_players(screen, drawer, top_content, client_state, interaction_map)
    _render_hand(screen, drawer, bottom_content, client_state, interaction_map)


def _render_rows_and_players(
    screen,
    drawer: PrimitiveDrawer,
    rect,
    client_state: ClientState,
    interaction_map: object,
) -> None:
    public_state = client_state.public_state
    if public_state is None:
        drawer.draw_wrapped_lines(screen, ["No public_state available."], rect)
        return

    info_lines = [
        f"round={public_state.round_no} trick={public_state.trick_no} phase={public_state.phase_info.phase.value}",
        f"message: {public_state.phase_info.message or '-'}",
    ]
    info_height = drawer.measure_wrapped_lines(info_lines, max_width=rect.width, role="small")
    info_rect = rect.copy()
    info_rect.height = info_height
    info_bottom = drawer.draw_wrapped_lines(screen, info_lines, info_rect, role="small", color=TEXT_MUTED)

    y = info_bottom + 10
    row_target_by_id = {target.row_id: target for target in interaction_map.row_targets}
    row_area_height = 132
    row_width = max(120, (rect.width - 18) // max(1, len(public_state.rows)))

    for index, row in enumerate(public_state.rows):
        target_rect = row_target_by_id[row.row_id].rect if row.row_id in row_target_by_id else None
        fallback_rect = rect.copy()
        fallback_rect.left = rect.left + index * row_width
        fallback_rect.top = y
        fallback_rect.width = row_width - 8
        fallback_rect.height = row_area_height
        _draw_row(
            screen,
            drawer,
            target_rect or fallback_rect,
            row.row_id,
            row.cards,
            selectable=_is_row_selectable(client_state, row.row_id),
        )

    players_top = y + row_area_height + 20
    drawer.draw_text(screen, "Scores", (rect.left, players_top), role="small", color=TEXT_MUTED)
    players_y = players_top + 22
    for player in public_state.players:
        marker = " <you>" if player.player_id == client_state.own_player_id else ""
        line = f"{player.name}: {player.score} points, {player.hand_count} cards{marker}"
        drawer.draw_text(screen, line, (rect.left, players_y), role="body")
        players_y += 26


def _render_hand(
    screen,
    drawer: PrimitiveDrawer,
    rect,
    client_state: ClientState,
    interaction_map: object,
) -> None:
    player_state = client_state.player_state
    if player_state is None:
        drawer.draw_wrapped_lines(screen, ["No player_state available."], rect)
        return

    info_lines = [
        f"player: {player_state.self_player_name()}",
        f"pending_action: {client_state.pending_action.value}",
        "click a card to send the choice",
    ]
    if player_state.phase_info.phase == Phase.CHOOSE_ROW and player_state.pending_card_value() is not None:
        info_lines.append(f"pending_card: {player_state.pending_card_value()}")

    info_height = drawer.measure_wrapped_lines(info_lines, max_width=rect.width, role="small")
    info_rect = rect.copy()
    info_rect.height = info_height
    drawer.draw_wrapped_lines(screen, info_lines, info_rect, role="small", color=TEXT_MUTED)

    target_by_value = {target.card_value: target for target in interaction_map.card_targets}
    for card in player_state.hand:
        target = target_by_value.get(card.value)
        if target is None:
            continue
        drawer.draw_card(screen, target.rect, value=card.value, bullheads=card.bullheads)

    if player_state.phase_info.phase == Phase.CHOOSE_ROW and player_state.pending_card_value() is not None:
        hint_rect = rect.copy()
        hint_rect.left = rect.right - 140
        hint_rect.top = rect.top
        hint_rect.width = 120
        hint_rect.height = 32
        drawer.draw_badge(screen, hint_rect, text=f"take {player_state.pending_card_value()}", active=True)


def _draw_row(screen, drawer: PrimitiveDrawer, rect, row_id, cards, *, selectable: bool) -> None:
    content_rect = drawer.draw_panel(screen, rect, title=str(row_id))
    drawer.draw_text(
        screen,
        f"bullheads={sum(card.bullheads for card in cards)}",
        (content_rect.left, content_rect.top),
        role="small",
        color=ACCENT if selectable else TEXT_MUTED,
    )
    card_y = content_rect.top + 24
    for index, card in enumerate(cards):
        card_rect = content_rect.copy()
        card_rect.left = content_rect.left + index * 72
        card_rect.top = card_y
        card_rect.width = 64
        card_rect.height = 52
        drawer.draw_card(screen, card_rect, value=card.value, bullheads=card.bullheads, selected=selectable)


def _is_row_selectable(client_state: ClientState, row_id) -> bool:
    player_state = client_state.player_state
    if player_state is None:
        return False
    if player_state.phase_info.phase != Phase.CHOOSE_ROW:
        return False
    return row_id in player_state.get_selectable_row_ids_for_choose_row()


def _render_sidebar(
    screen,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    last_action_summary: str,
    interaction_map: object,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.sidebar_rect, title="State summary")
    y = content_rect.top

    entries = [
        ("client_mode", client_state.client_mode.value),
        ("pending_action", client_state.pending_action.value),
        ("own_client_id", client_state.own_client_id or "-"),
        ("own_player_id", client_state.own_player_id or "-"),
        ("lobby_submenu", client_state.navigation_state.lobby_submenu),
        ("session_error", client_state.session_error or "-"),
        ("presentation", str(len(client_state.pending_presentation_events))),
        ("frame", str(frame_count)),
    ]

    for key, value in entries:
        drawer.draw_key_value(screen, key, value, (content_rect.left, y))
        y += 28

    drawer.draw_text(screen, "last_gui_action", (content_rect.left, y + 6), role="small", color=TEXT_MUTED)
    action_rect = content_rect.copy()
    action_rect.top = y + 28
    action_rect.height = 72
    drawer.draw_wrapped_lines(screen, [last_action_summary], action_rect, role="small", color=ACCENT)

    flash_text = client_state.flash_message.text if client_state.flash_message is not None else "No flash message"
    drawer.draw_text(screen, "flash_message", (content_rect.left, action_rect.bottom + 10), role="small", color=TEXT_MUTED)
    flash_rect = content_rect.copy()
    flash_rect.top = action_rect.bottom + 32
    flash_rect.height = 64
    drawer.draw_wrapped_lines(screen, [flash_text], flash_rect, role="body", color=ACCENT)

    events_rect = content_rect.copy()
    events_rect.top = flash_rect.bottom + 18
    events_bottom = layout.sidebar_rect.bottom - 70
    events_rect.height = max(40, events_bottom - events_rect.top)
    drawer.draw_text(screen, "presentation events", (events_rect.left, events_rect.top), role="small", color=TEXT_MUTED)
    events_rect.top += 22
    event_lines = [_format_presentation_event(event) for event in client_state.pending_presentation_events]
    if not event_lines:
        event_lines = ["No pending presentation events."]
    drawer.draw_wrapped_lines(screen, event_lines, events_rect, role="small")

    if interaction_map.continue_target is not None:
        drawer.draw_badge(screen, interaction_map.continue_target.rect, text="Continue [Space]", active=True)


def _format_presentation_event(event: PresentationEvent) -> str:
    if isinstance(event, PresentationCardsRevealed):
        cards = ", ".join(f"{play.player_name}:{play.card_value}" for play in event.plays)
        return f"cards revealed -> {cards}"
    if isinstance(event, PresentationRowChoiceRequired):
        return f"row choice required -> {event.player_name} with {event.card_value}"
    if isinstance(event, PresentationRowChosen):
        return f"row chosen -> {event.player_name} takes {event.row_id}"
    if isinstance(event, PresentationRowTaken):
        return f"row taken -> {event.player_name} got {event.bullheads} bullheads"
    if isinstance(event, PresentationOverflowResolved):
        return f"overflow resolved -> {event.player_name} got {event.bullheads} bullheads"
    if isinstance(event, PresentationTrickFinished):
        return "trick finished"
    return event.__class__.__name__


def _render_footer(screen, drawer: PrimitiveDrawer, layout: DemoLayout) -> None:
    content_rect = drawer.draw_panel(screen, layout.footer_rect)
    drawer.draw_wrapped_lines(
        screen,
        [
            "ESC quit",
            "Space continue presentation",
            "Mouse for seats, buttons, cards and rows",
        ],
        content_rect,
        role="small",
        color=TEXT_MUTED,
    )
