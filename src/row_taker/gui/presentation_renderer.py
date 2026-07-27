from __future__ import annotations

from typing import Any

import pygame

from row_taker.gui.animation import AnimationClock, lerp_rect
from row_taker.gui.assets import GuiAssets
from row_taker.gui.board_layout import (
    BoardGeometry,
    hand_card_placements,
    row_card_placements,
)
from row_taker.gui.card import GuiCard
from row_taker.gui.game_visual_state import GameVisualState
from row_taker.gui.presentation_visuals import PresentationVisuals
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_overlay_panel
from row_taker.gui_common.primitives import PrimitiveDrawer

THEME = DEFAULT_THEME
PALETTE = THEME.palette


def draw_presentation_card_motion(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    presentation_visuals: PresentationVisuals,
    assets: GuiAssets,
    animation_clock: AnimationClock,
    *,
    opponent_slots: tuple[Any, ...],
) -> None:
    """Draw the animated card that belongs to the front-most presentation event."""

    if not presentation_visuals.has_event:
        return
    if presentation_visuals.active_row_id is None:
        return
    if not presentation_visuals.focus_card_values:
        return

    card_value = presentation_visuals.replacement_card_value or presentation_visuals.focus_card_values[0]
    source_rect = _presentation_motion_source_rect(
        geometry,
        visual_state,
        presentation_visuals,
        card_value=card_value,
        opponent_slots=opponent_slots,
    )
    target_rect = _presentation_motion_target_rect(geometry, visual_state, presentation_visuals)
    if source_rect is None or target_rect is None:
        return

    progress = animation_clock.ease_out_cubic(duration_frames=32)
    current_rect = lerp_rect(source_rect, target_rect, progress)
    shadow_rect = current_rect.inflate(12, 12).move(4, 5)
    shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shadow, pygame.Color(0, 0, 0, 80), shadow.get_rect(), border_radius=THEME.spacing.card_radius + 4)
    screen.blit(shadow, shadow_rect)

    path_color = pygame.Color(PALETTE.accent_hover)
    path_color.a = max(35, 120 - round(progress * 70))
    _draw_motion_path(screen, source_rect.center, target_rect.center, path_color)

    GuiCard.from_card_value(card_value, current_rect, selected=True).draw(screen, drawer=drawer, assets=assets)


def draw_presentation_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    presentation_visuals: PresentationVisuals,
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    """Draw the text/card panel for the current presentation step."""

    events_rect = pygame.Rect(
        geometry.stats_rect.left,
        geometry.stats_rect.bottom - 174,
        geometry.stats_rect.width,
        128,
    )
    _draw_overlay_box(screen, events_rect)
    _draw_presentation_accent(screen, events_rect, animation_clock)

    drawer.draw_text(
        screen,
        presentation_visuals.headline,
        (events_rect.left + 12, events_rect.top + 10),
        role="small",
        color=animation_clock.pulsed_color(PALETTE.accent, PALETTE.accent_hover, period_frames=72),
    )

    if presentation_visuals.focus_card_values:
        _draw_presentation_card_strip(
            screen,
            drawer,
            events_rect,
            card_values=presentation_visuals.focus_card_values,
            assets=assets,
        )
        text_top = events_rect.top + 74
    else:
        text_top = events_rect.top + 34

    lines = list(presentation_visuals.details[:2])
    if lines:
        text_rect = pygame.Rect(events_rect.left + 12, text_top, events_rect.width - 24, events_rect.bottom - text_top - 6)
        drawer.draw_wrapped_lines(screen, lines, text_rect, role="tiny", color=PALETTE.text_primary)


def _presentation_motion_source_rect(
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    presentation_visuals: PresentationVisuals,
    *,
    card_value: int,
    opponent_slots: tuple[Any, ...],
) -> pygame.Rect | None:
    if presentation_visuals.active_player_id == visual_state.own_player_id:
        hand_cards = visual_state.visible_hand
        placements = hand_card_placements(geometry, card_count=len(hand_cards))
        for card, placement in zip(hand_cards, placements, strict=False):
            if card.card_value == card_value:
                return placement.rect
        fallback = pygame.Rect(0, 0, *geometry.staged_card_size)
        fallback.center = geometry.hand_rect.center
        return fallback

    for slot in opponent_slots:
        if slot.player_id == presentation_visuals.active_player_id:
            return slot.geometry.staged_card.rect

    return None


def _presentation_motion_target_rect(
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    presentation_visuals: PresentationVisuals,
) -> pygame.Rect | None:
    if presentation_visuals.active_row_id is None:
        return None

    for row_index, row in enumerate(visual_state.rows):
        if row.row_id != presentation_visuals.active_row_id:
            continue

        placements = row_card_placements(
            geometry,
            row_index=row_index,
            card_count=max(1, len(row.cards)),
        )
        if placements:
            return placements[-1].rect

        target = pygame.Rect(0, 0, *geometry.row_card_size)
        target.center = geometry.row_columns[row_index].center
        return target

    return None


def _draw_motion_path(
    screen: pygame.Surface,
    start: tuple[int, int],
    end: tuple[int, int],
    color: pygame.Color,
) -> None:
    left = min(start[0], end[0])
    top = min(start[1], end[1])
    width = max(1, abs(end[0] - start[0]))
    height = max(1, abs(end[1] - start[1]))
    surface = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
    local_start = (start[0] - left + 4, start[1] - top + 4)
    local_end = (end[0] - left + 4, end[1] - top + 4)
    pygame.draw.line(surface, color, local_start, local_end, width=2)
    screen.blit(surface, (left - 4, top - 4))


def _draw_presentation_accent(
    screen: pygame.Surface,
    rect: pygame.Rect,
    animation_clock: AnimationClock,
) -> None:
    accent_rect = pygame.Rect(rect.left + 10, rect.top + 7, 4, rect.height - 14)
    accent_color = animation_clock.pulsed_color(
        PALETTE.accent,
        PALETTE.accent_hover,
        period_frames=72,
    )
    accent_color.a = animation_clock.pulse_alpha(period_frames=72, low=120, high=235)
    accent_surface = pygame.Surface(accent_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(accent_surface, accent_color, accent_surface.get_rect(), border_radius=3)
    screen.blit(accent_surface, accent_rect)


def _draw_presentation_card_strip(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    card_values: tuple[int, ...],
    assets: GuiAssets,
) -> None:
    max_cards = min(4, len(card_values))
    card_width = max(32, min(44, (rect.width - 28) // max(1, max_cards)))
    card_size = (card_width, round(card_width * 1.5))
    x = rect.left + 12
    y = rect.top + 34
    for value in card_values[:max_cards]:
        card_rect = pygame.Rect(x, y, card_size[0], card_size[1])
        GuiCard.from_card_value(value, card_rect, selected=True).draw(screen, drawer=drawer, assets=assets)
        x += card_width + 8

    remaining = len(card_values) - max_cards
    if remaining > 0:
        drawer.draw_text(screen, f"+{remaining}", (x + 2, y + 18), role="small", color=PALETTE.text_muted)


def _draw_overlay_box(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_overlay_panel(screen, rect, theme=THEME)
