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
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import TEXT_MUTED, PrimitiveDrawer


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
        f'Modus={client_state.client_mode.value}, pending_action={client_state.pending_action.value}'
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
            'ESC beenden',
            'Leertaste Präsentation fortsetzen',
            'Maus für Plätze, Buttons, Karten und Reihen',
        ],
        content_rect,
        role='small',
        color=TEXT_MUTED,
    )


def format_presentation_event(event: PresentationEvent) -> str:
    if isinstance(event, PresentationCardsRevealed):
        cards = ', '.join(f'{play.player_name}:{play.card_value}' for play in event.plays)
        return f'Karten aufgedeckt -> {cards}'
    if isinstance(event, PresentationRowChoiceRequired):
        return f'Reihenauswahl nötig -> {event.player_name} mit {event.card_value}'
    if isinstance(event, PresentationRowChosen):
        return f'Reihe gewählt -> {event.player_name} nimmt {event.row_id}'
    if isinstance(event, PresentationRowTaken):
        return f'Reihe genommen -> {event.player_name} erhielt {event.bullheads} Hornochsen'
    if isinstance(event, PresentationOverflowResolved):
        return f'Überlauf aufgelöst -> {event.player_name} erhielt {event.bullheads} Hornochsen'
    if isinstance(event, PresentationTrickFinished):
        return 'Stich beendet'
    return event.__class__.__name__
