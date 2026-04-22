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
from row_taker.gui_demo.layout import DemoLayout
from row_taker.gui_demo.primitives import TEXT_MUTED, PrimitiveDrawer


def render_standard_header(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.header_rect)
    drawer.draw_text(screen, 'Row-Taker GUI Demo', (content_rect.left, content_rect.top), role='title')
    subtitle = (
        'Einfaches pygame-Frontend auf dem gemeinsamen ClientState. '
        f'Mode={client_state.client_mode.value}, pending_action={client_state.pending_action.value}'
    )
    drawer.draw_text(
        screen,
        subtitle,
        (content_rect.left, content_rect.top + 34),
        role='small',
        color=TEXT_MUTED,
    )


def render_standard_footer(screen: pygame.Surface, drawer: PrimitiveDrawer, layout: DemoLayout) -> None:
    content_rect = drawer.draw_panel(screen, layout.footer_rect)
    drawer.draw_wrapped_lines(
        screen,
        [
            'ESC quit',
            'Space continue presentation',
            'Mouse for seats, buttons, cards and rows',
        ],
        content_rect,
        role='small',
        color=TEXT_MUTED,
    )


def format_presentation_event(event: PresentationEvent) -> str:
    if isinstance(event, PresentationCardsRevealed):
        cards = ', '.join(f'{play.player_name}:{play.card_value}' for play in event.plays)
        return f'cards revealed -> {cards}'
    if isinstance(event, PresentationRowChoiceRequired):
        return f'row choice required -> {event.player_name} with {event.card_value}'
    if isinstance(event, PresentationRowChosen):
        return f'row chosen -> {event.player_name} takes {event.row_id}'
    if isinstance(event, PresentationRowTaken):
        return f'row taken -> {event.player_name} got {event.bullheads} bullheads'
    if isinstance(event, PresentationOverflowResolved):
        return f'overflow resolved -> {event.player_name} got {event.bullheads} bullheads'
    if isinstance(event, PresentationTrickFinished):
        return 'trick finished'
    return event.__class__.__name__
