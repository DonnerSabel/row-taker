from __future__ import annotations

import pygame

from row_taker.gui.animation import AnimationClock
from row_taker.gui.assets import GuiAssets
from row_taker.gui.board_layout import (
    BoardGeometry,
    CardPlacement,
    row_card_placements,
)
from row_taker.gui.card import GuiCard
from row_taker.gui.game_interaction import GameScreenTargets
from row_taker.gui.game_visual_state import (
    GameVisualState,
    RowEmphasis,
    VisualCard,
)
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_badge

THEME = DEFAULT_THEME
PALETTE = THEME.palette


def draw_rows(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    """Draw all board rows from the prepared visual state and geometry."""

    row_target_by_id = {target.row_id: target for target in game_targets.row_targets}

    for row_index, (row, column_rect) in enumerate(
        zip(visual_state.rows, geometry.row_columns, strict=False)
    ):
        target = row_target_by_id.get(row.row_id)
        selectable = row.row_id in visual_state.interaction.selectable_row_ids
        hovered = bool(target.hovered) if target is not None else False
        placements = row_card_placements(
            geometry,
            row_index=row_index,
            card_count=len(row.cards),
        )
        taken_values = tuple(card.card_value for card in row.taken_cards)
        _draw_row_column(
            screen,
            drawer,
            column_rect,
            row_id=row.row_id,
            cards=row.cards,
            placements=placements,
            selectable=selectable,
            hovered=hovered,
            emphasis=row.emphasis,
            taken_card_values=taken_values,
            assets=assets,
            animation_clock=animation_clock,
        )


def _draw_row_column(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    row_id: object,
    cards: tuple[VisualCard, ...],
    placements: tuple[CardPlacement, ...],
    selectable: bool,
    hovered: bool,
    emphasis: RowEmphasis,
    taken_card_values: tuple[int, ...],
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    lane_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    lane_fill = (
        PALETTE.lane_overlay_active if emphasis != "none" or hovered else PALETTE.lane_overlay
    )
    pygame.draw.rect(lane_surface, lane_fill, lane_surface.get_rect(), border_radius=8)
    screen.blit(lane_surface, rect)

    border = _row_border_color(
        selectable=selectable,
        hovered=hovered,
        emphasis=emphasis,
    )
    if emphasis != "none":
        _draw_pulsing_outline(screen, rect, border, animation_clock, max_inflate=12)
    border_width = 4 if emphasis != "none" or hovered else 3 if selectable else 1
    pygame.draw.rect(screen, border, rect, border_width, border_radius=8)

    label_color = border if selectable or hovered or emphasis != "none" else PALETTE.text_muted
    drawer.draw_text(
        screen,
        str(row_id),
        (rect.left + 8, rect.top + 6),
        role="small",
        color=label_color,
    )

    if emphasis in {"taken", "overflow"}:
        _draw_row_taken_badge(
            screen,
            drawer,
            rect,
            taken_card_values=taken_card_values,
        )

    for card, placement in zip(cards, placements, strict=False):
        selected = selectable or hovered or emphasis != "none"
        GuiCard(
            card_value=card.card_value,
            bullheads=card.bullheads,
            rect=placement.rect,
            selected=selected,
        ).draw(screen, drawer=drawer, assets=assets)


def _row_border_color(
    *,
    selectable: bool,
    hovered: bool,
    emphasis: RowEmphasis,
) -> pygame.Color:
    if emphasis == "placed":
        return PALETTE.row_placed
    if emphasis == "choice":
        return PALETTE.row_choice
    if emphasis == "taken":
        return PALETTE.row_taken
    if emphasis == "overflow":
        return PALETTE.row_overflow
    if hovered:
        return PALETTE.accent_hover
    if selectable:
        return PALETTE.accent
    return PALETTE.row_neutral


def _draw_row_taken_badge(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    taken_card_values: tuple[int, ...],
) -> None:
    cards = ", ".join(str(value) for value in taken_card_values)
    if not cards:
        return

    badge_rect = pygame.Rect(
        rect.left + 8,
        rect.bottom - 34,
        max(1, rect.width - 16),
        26,
    )
    draw_badge(
        screen,
        drawer,
        badge_rect,
        f"nimmt: {cards}",
        fill=PALETTE.taken_badge_fill,
        border=PALETTE.taken_badge_border,
        theme=THEME,
    )


def _draw_pulsing_outline(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: pygame.Color,
    animation_clock: AnimationClock,
    *,
    max_inflate: int,
) -> None:
    inflate = animation_clock.pulse_inflate(
        period_frames=54,
        max_pixels=max_inflate,
    )
    glow_rect = rect.inflate(inflate, inflate)
    alpha = animation_clock.pulse_alpha(period_frames=54, low=42, high=115)
    overlay = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
    glow_color = pygame.Color(color)
    glow_color.a = alpha
    pygame.draw.rect(
        overlay,
        glow_color,
        overlay.get_rect(),
        width=3,
        border_radius=10,
    )
    screen.blit(overlay, glow_rect)
