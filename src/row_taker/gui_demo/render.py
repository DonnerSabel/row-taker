from __future__ import annotations

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
from row_taker.engine.game import Phase
from row_taker.gui_demo.layout import DemoLayout
from row_taker.gui_demo.primitives import (
    ACCENT,
    TEXT_MUTED,
    WINDOW_BACKGROUND,
    PrimitiveDrawer,
)


def render_app(
    screen,
    *,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    active_demo_scene: str | None,
) -> None:
    screen.fill(WINDOW_BACKGROUND)
    _render_header(screen, drawer, layout, client_state, active_demo_scene)
    _render_main_area(screen, drawer, layout, client_state)
    _render_sidebar(screen, drawer, layout, client_state, frame_count)
    _render_footer(screen, drawer, layout, active_demo_scene)


def _render_header(
    screen,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    active_demo_scene: str | None,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.header_rect)
    drawer.draw_text(screen, "Row-Taker GUI Demo", (content_rect.left, content_rect.top), role="title")
    subtitle = (
        "Patch 2: lobby and game panels render the real shared structures. "
        f"Mode={client_state.client_mode.value}, pending_action={client_state.pending_action.value}"
    )
    drawer.draw_text(
        screen,
        subtitle,
        (content_rect.left, content_rect.top + 34),
        role="small",
        color=TEXT_MUTED,
    )

    if active_demo_scene is not None:
        badge_rect = layout.header_rect.copy()
        badge_rect.width = 160
        badge_rect.height = 30
        badge_rect.top = content_rect.top
        badge_rect.right = layout.header_rect.right - 12
        drawer.draw_badge(screen, badge_rect, text=f"demo:{active_demo_scene}", active=True)


def _render_main_area(screen, drawer: PrimitiveDrawer, layout: DemoLayout, client_state: ClientState) -> None:
    if client_state.client_mode.value == "lobby":
        _render_lobby_panels(screen, drawer, layout, client_state)
        return
    if client_state.public_state is not None or client_state.player_state is not None:
        _render_game_panels(screen, drawer, layout, client_state)
        return

    content_rect = drawer.draw_panel(screen, layout.main_rect, title="Current view")
    drawer.draw_wrapped_lines(
        screen,
        [
            "No lobby or game data is available yet.",
            "This should only happen outside the built-in demo scenes.",
        ],
        content_rect,
    )


def _render_lobby_panels(screen, drawer: PrimitiveDrawer, layout: DemoLayout, client_state: ClientState) -> None:
    top_content = drawer.draw_panel(screen, layout.main_top_rect, title="Lobby seats")
    bottom_content = drawer.draw_panel(screen, layout.main_bottom_rect, title="Participants")

    lobby_view = client_state.lobby_view
    if lobby_view is None:
        drawer.draw_wrapped_lines(screen, ["No lobby view available."], top_content)
        return

    y = top_content.top
    drawer.draw_text(
        screen,
        f"server_endpoint: {lobby_view.server_endpoint or '-'}",
        (top_content.left, y),
        role="small",
        color=TEXT_MUTED,
    )
    y += 28

    for seat in lobby_view.seats:
        occupant = seat.occupant_display_name or "-"
        seat_text = f"Seat {seat.seat_index + 1}: {occupant}"
        if seat.occupant_kind:
            seat_text += f" [{seat.occupant_kind}]"
        if client_state.navigation_state.selected_seat_index == seat.seat_index:
            seat_text += "  <selected>"
        drawer.draw_text(screen, seat_text, (top_content.left, y), role="body")
        y += 28

    participant_lines = []
    for participant in lobby_view.participants:
        seat_label = "-" if participant.seat_index is None else str(participant.seat_index + 1)
        participant_lines.append(
            f"{participant.display_name} [{participant.participant_kind}] seat={seat_label} endpoint={participant.endpoint or '-'}"
        )
    participant_lines.extend(
        [
            "",
            "Planned next step: seats become clickable and map to lobby commands.",
        ]
    )
    drawer.draw_wrapped_lines(screen, participant_lines, bottom_content, role="body")


def _render_game_panels(screen, drawer: PrimitiveDrawer, layout: DemoLayout, client_state: ClientState) -> None:
    top_content = drawer.draw_panel(screen, layout.main_top_rect, title="Rows and players")
    bottom_content = drawer.draw_panel(screen, layout.main_bottom_rect, title="Own hand")

    _render_rows_and_players(screen, drawer, top_content, client_state)
    _render_hand(screen, drawer, bottom_content, client_state)


def _render_rows_and_players(screen, drawer: PrimitiveDrawer, rect, client_state: ClientState) -> None:
    public_state = client_state.public_state
    if public_state is None:
        drawer.draw_wrapped_lines(screen, ["No public_state available."], rect)
        return

    y = rect.top
    phase_message = public_state.phase_info.message or "-"
    drawer.draw_text(
        screen,
        f"round={public_state.round_no} trick={public_state.trick_no} phase={public_state.phase_info.phase.value}",
        (rect.left, y),
        role="small",
        color=TEXT_MUTED,
    )
    y += 24
    drawer.draw_text(screen, f"message: {phase_message}", (rect.left, y), role="small", color=TEXT_MUTED)
    y += 34

    row_area_height = 132
    row_width = max(120, (rect.width - 18) // max(1, len(public_state.rows)))
    for index, row in enumerate(public_state.rows):
        row_rect = rect.copy()
        row_rect.left = rect.left + index * row_width
        row_rect.top = y
        row_rect.width = row_width - 8
        row_rect.height = row_area_height
        _draw_row(
            screen,
            drawer,
            row_rect,
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


def _render_hand(screen, drawer: PrimitiveDrawer, rect, client_state: ClientState) -> None:
    player_state = client_state.player_state
    if player_state is None:
        drawer.draw_wrapped_lines(screen, ["No player_state available."], rect)
        return

    info_lines = [
        f"player: {player_state.self_player_name()}",
        f"pending_action: {client_state.pending_action.value}",
    ]
    if player_state.phase_info.phase == Phase.CHOOSE_ROW and player_state.pending_card_value() is not None:
        info_lines.append(f"pending_card: {player_state.pending_card_value()}")
    drawer.draw_wrapped_lines(screen, info_lines, rect, role="small", color=TEXT_MUTED)

    cards_top = rect.top + 54
    card_width = 78
    card_height = 58
    row_gap = 10
    col_gap = 10
    columns = max(1, rect.width // (card_width + col_gap))
    for index, card in enumerate(player_state.hand):
        row_index = index // columns
        column_index = index % columns
        card_rect = rect.copy()
        card_rect.left = rect.left + column_index * (card_width + col_gap)
        card_rect.top = cards_top + row_index * (card_height + row_gap)
        card_rect.width = card_width
        card_rect.height = card_height
        drawer.draw_card(screen, card_rect, value=card.value, bullheads=card.bullheads)

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

    flash_text = client_state.flash_message.text if client_state.flash_message is not None else "No flash message"
    drawer.draw_text(screen, "flash_message", (content_rect.left, y + 8), role="small", color=TEXT_MUTED)
    flash_rect = content_rect.copy()
    flash_rect.top = y + 30
    flash_rect.height = 72
    drawer.draw_wrapped_lines(screen, [flash_text], flash_rect, role="body", color=ACCENT)

    events_rect = content_rect.copy()
    events_rect.top = flash_rect.bottom + 18
    drawer.draw_text(screen, "presentation events", (events_rect.left, events_rect.top), role="small", color=TEXT_MUTED)
    events_rect.top += 22
    event_lines = [_format_presentation_event(event) for event in client_state.pending_presentation_events]
    if not event_lines:
        event_lines = ["No pending presentation events."]
    drawer.draw_wrapped_lines(screen, event_lines, events_rect, role="small")


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


def _render_footer(screen, drawer: PrimitiveDrawer, layout: DemoLayout, active_demo_scene: str | None) -> None:
    content_rect = drawer.draw_panel(screen, layout.footer_rect)
    footer_lines = [
        "ESC quit",
        "1 lobby   2 choose-card   3 choose-row   4 presentation",
        "Patch 2 goal: real lobby/game rendering from shared structures.",
    ]
    if active_demo_scene is None:
        footer_lines[1] = "Scene hotkeys disabled because the app is running with an external ClientState."
    drawer.draw_wrapped_lines(screen, footer_lines, content_rect, role="small", color=TEXT_MUTED)
