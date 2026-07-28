from __future__ import annotations

from collections.abc import Mapping

import pygame

from row_taker.engine.game.models import PlayerID
from row_taker.gui.animation import AnimationClock, lerp_rect
from row_taker.gui.assets import GuiAssets
from row_taker.gui.board_layout import BoardGeometry, row_card_placements
from row_taker.gui.card import GuiCard
from row_taker.gui.game_visual_state import (
    GameVisualState,
    PlayerPlayAnchor,
    RowCardAnchor,
    VisualMovingCard,
    VisualPresentationPanel,
)
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_overlay_panel

THEME = DEFAULT_THEME
PALETTE = THEME.palette


def draw_presentation_card_motion(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    assets: GuiAssets,
    *,
    player_staged_card_rects: Mapping[PlayerID, pygame.Rect],
) -> None:
    """Draw all semantic card motions from the resolved visual state."""

    for moving_card in visual_state.moving_cards:
        resolved = resolve_visual_card_motion_rects(
            geometry,
            visual_state,
            moving_card,
            player_staged_card_rects=player_staged_card_rects,
        )
        if resolved is None:
            continue
        source_rect, target_rect = resolved
        _draw_moving_card(
            screen,
            drawer,
            source_rect=source_rect,
            target_rect=target_rect,
            card_value=moving_card.card_value,
            progress=moving_card.progress,
            assets=assets,
        )


def resolve_visual_card_motion_rects(
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    moving_card: VisualMovingCard,
    *,
    player_staged_card_rects: Mapping[PlayerID, pygame.Rect],
) -> tuple[pygame.Rect, pygame.Rect] | None:
    """Resolve semantic motion anchors through current production geometry."""

    source_rect = _visual_motion_source_rect(
        moving_card.source,
        player_staged_card_rects=player_staged_card_rects,
    )
    target_rect = _visual_motion_target_rect(
        geometry,
        visual_state,
        moving_card.target,
    )
    if source_rect is None or target_rect is None:
        return None
    return source_rect, target_rect


def _visual_motion_source_rect(
    source: PlayerPlayAnchor,
    *,
    player_staged_card_rects: Mapping[PlayerID, pygame.Rect],
) -> pygame.Rect | None:
    return player_staged_card_rects.get(source.player_id)


def _visual_motion_target_rect(
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    target: RowCardAnchor,
) -> pygame.Rect | None:
    for row_index, row in enumerate(visual_state.rows):
        if row.row_id != target.row_id:
            continue
        if target.card_index < 0:
            return None
        placements = row_card_placements(
            geometry,
            row_index=row_index,
            card_count=max(len(row.cards), target.card_index + 1),
        )
        if target.card_index >= len(placements):
            return None
        return placements[target.card_index].rect
    return None


def _draw_moving_card(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    *,
    source_rect: pygame.Rect,
    target_rect: pygame.Rect,
    card_value: int,
    progress: float,
    assets: GuiAssets,
) -> None:
    current_rect = lerp_rect(source_rect, target_rect, progress)
    shadow_rect = current_rect.inflate(12, 12).move(4, 5)
    shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        shadow,
        pygame.Color(0, 0, 0, 80),
        shadow.get_rect(),
        border_radius=THEME.spacing.card_radius + 4,
    )
    screen.blit(shadow, shadow_rect)

    path_color = pygame.Color(PALETTE.accent_hover)
    path_color.a = max(35, 120 - round(progress * 70))
    _draw_motion_path(screen, source_rect.center, target_rect.center, path_color)

    GuiCard.from_card_value(card_value, current_rect, selected=True).draw(
        screen,
        drawer=drawer,
        assets=assets,
    )


def draw_presentation_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    panel: VisualPresentationPanel,
    animation_clock: AnimationClock,
) -> None:
    """Draw the text-only panel in the prepared sidebar rectangle."""

    events_rect = rect
    _draw_overlay_box(screen, events_rect)
    _draw_presentation_accent(screen, events_rect, animation_clock)

    drawer.draw_text(
        screen,
        panel.headline,
        (events_rect.left + 12, events_rect.top + 10),
        role="small",
        color=animation_clock.pulsed_color(
            PALETTE.accent,
            PALETTE.accent_hover,
            period_frames=72,
        ),
    )

    text_top = events_rect.top + 34
    lines = list(panel.details[:2])
    if lines:
        text_rect = pygame.Rect(
            events_rect.left + 12,
            text_top,
            events_rect.width - 24,
            max(1, events_rect.bottom - text_top - 6),
        )
        drawer.draw_wrapped_lines(
            screen,
            lines,
            text_rect,
            role="tiny",
            color=PALETTE.text_primary,
        )


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
    accent_color.a = animation_clock.pulse_alpha(
        period_frames=72,
        low=120,
        high=235,
    )
    accent_surface = pygame.Surface(accent_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(
        accent_surface,
        accent_color,
        accent_surface.get_rect(),
        border_radius=3,
    )
    screen.blit(accent_surface, accent_rect)


def _draw_overlay_box(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_overlay_panel(screen, rect, theme=THEME)
