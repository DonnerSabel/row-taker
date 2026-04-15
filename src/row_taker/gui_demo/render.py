from __future__ import annotations

from row_taker.client.state import ClientState
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
) -> None:
    screen.fill(WINDOW_BACKGROUND)
    _render_header(screen, drawer, layout, client_state)
    _render_main_panel(screen, drawer, layout, client_state)
    _render_sidebar(screen, drawer, layout, client_state, frame_count)
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
        "Second frontend prototype: pygame shell around ClientState. "
        f"Mode={client_state.client_mode.value}, "
        f"pending_action={client_state.pending_action.value}"
    )
    drawer.draw_text(
        screen,
        subtitle,
        (content_rect.left, content_rect.top + 34),
        role="small",
        color=TEXT_MUTED,
    )


def _render_main_panel(
    screen,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.main_rect, title="Current view")
    lines = [
        "Patch 1 deliberately keeps the frontend simple.",
        "",
        "This window already renders the shared client structures instead of using the old gui package.",
        "The next patch can replace these placeholder paragraphs with lobby and game panels.",
        "",
    ]

    if client_state.lobby_view is None:
        lines.append("Lobby view: not connected yet.")
    else:
        lines.append(
            f"Lobby view: {client_state.lobby_view.seat_count} seats, "
            f"{len(client_state.lobby_view.participants)} participants."
        )

    if client_state.public_state is None:
        lines.append("Public game state: not available yet.")
    else:
        lines.append(f"Public game state: {len(client_state.public_state.rows)} rows visible.")

    if client_state.player_state is None:
        lines.append("Own player state: not available yet.")
    else:
        lines.append(f"Own player state: {len(client_state.player_state.hand)} cards in hand.")

    drawer.draw_wrapped_lines(screen, lines, content_rect)


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

    flash_text = (
        client_state.flash_message.text
        if client_state.flash_message is not None
        else "No flash message"
    )
    flash_label_y = y + 8
    drawer.draw_text(
        screen,
        "flash_message",
        (content_rect.left, flash_label_y),
        role="small",
        color=TEXT_MUTED,
    )
    flash_rect = content_rect.copy()
    flash_rect.top = flash_label_y + 22
    drawer.draw_wrapped_lines(screen, [flash_text], flash_rect, role="body", color=ACCENT)


def _render_footer(screen, drawer: PrimitiveDrawer, layout: DemoLayout) -> None:
    content_rect = drawer.draw_panel(screen, layout.footer_rect)
    footer_lines = [
        "ESC quit",
        "Window resize is already supported",
        "Patch 1 goal: stable pygame app skeleton, layout, rendering, and isolated gui_demo package",
    ]
    drawer.draw_wrapped_lines(screen, footer_lines, content_rect, role="small", color=TEXT_MUTED)
