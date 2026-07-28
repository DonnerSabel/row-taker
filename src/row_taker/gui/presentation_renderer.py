from __future__ import annotations

from collections.abc import Mapping

import pygame

from row_taker.engine.game.models import PlayerID
from row_taker.gui.animation import lerp_rect
from row_taker.gui.assets import GuiAssets
from row_taker.gui.board_layout import BoardGeometry, row_card_placements
from row_taker.gui.card import GuiCard
from row_taker.gui.game_visual_state import (
    GameVisualState,
    PlayerPlayAnchor,
    RowCardAnchor,
    VisualMovingCard,
)
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.theme import DEFAULT_THEME

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
