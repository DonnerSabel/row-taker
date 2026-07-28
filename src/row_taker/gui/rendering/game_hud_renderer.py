from __future__ import annotations

from collections.abc import Mapping

import pygame

from row_taker.engine.game.models import PlayerID
from row_taker.gui.animation import AnimationClock
from row_taker.gui.assets import GuiAssets
from row_taker.gui.board_layout import BoardGeometry, hand_card_placements
from row_taker.gui.card import GuiCard
from row_taker.gui.game_interaction import GameScreenTargets
from row_taker.gui.game_visual_state import GameVisualState, MessageLevel
from row_taker.gui.presentation_renderer import draw_presentation_panel
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_button, draw_overlay_panel, draw_panel

THEME = DEFAULT_THEME
PALETTE = THEME.palette


def player_staged_card_rects(
    visual_state: GameVisualState,
    geometry: BoardGeometry,
) -> Mapping[PlayerID, pygame.Rect]:
    """Map every visible player id to the staged-card slot in its tile."""

    rects = {
        player.player_id: tile.card_placement.rect
        for player, tile in zip(
            visual_state.opponents,
            geometry.opponent_tiles,
            strict=False,
        )
    }
    own_player = visual_state.own_player
    if own_player is not None:
        rects[own_player.player_id] = geometry.own_player_tile.card_placement.rect
    return rects


def draw_opponent_tiles(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    assets: GuiAssets,
) -> None:
    """Draw compact opponent tiles in the artwork-independent sidebar."""

    opponents = visual_state.opponents
    prepared = tuple(
        zip(opponents, geometry.opponent_tiles, strict=False)
    )

    # Draw all tile backgrounds first. Cards are a separate layer because
    # neighbouring cards may intentionally overlap vertically.
    for _player, tile in prepared:
        _draw_player_tile_background(screen, tile.tile_rect)

    for player, tile in prepared:
        if player.staged_card_value is None:
            continue
        GuiCard.from_card_value(
            player.staged_card_value,
            tile.card_placement.rect,
        ).draw(
            screen,
            drawer=drawer,
            assets=assets,
        )

    for player, tile in prepared:
        _draw_player_tile_text(
            screen,
            drawer,
            info_rect=tile.info_rect,
            player_name=player.name,
            score=player.score,
        )


def draw_own_player_tile(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    assets: GuiAssets,
) -> None:
    """Draw the local player in the dedicated lower sidebar tile."""

    player = visual_state.own_player
    if player is None:
        return

    tile = geometry.own_player_tile
    _draw_player_tile_background(screen, tile.tile_rect)
    if player.staged_card_value is not None:
        GuiCard.from_card_value(
            player.staged_card_value,
            tile.card_placement.rect,
        ).draw(
            screen,
            drawer=drawer,
            assets=assets,
        )
    _draw_player_tile_text(
        screen,
        drawer,
        info_rect=tile.info_rect,
        player_name=player.name,
        score=player.score,
    )


def _draw_player_tile_background(
    screen: pygame.Surface,
    tile_rect: pygame.Rect,
) -> None:
    draw_panel(
        screen,
        tile_rect.inflate(-2, -4),
        radius=8,
        fill=PALETTE.panel_fill_soft,
        border=PALETTE.panel_border,
        border_width=1,
        alpha=150,
        theme=THEME,
    )


def _draw_player_tile_text(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    *,
    info_rect: pygame.Rect,
    player_name: str,
    score: int,
) -> None:
    name_role = "small"
    score_role = "tiny"
    name = _fit_text_to_width(
        drawer,
        player_name,
        max_width=info_rect.width,
        role=name_role,
    )
    score_text = f"{score} Hornochsen"

    name_font = drawer._font_for_role(name_role)
    score_font = drawer._font_for_role(score_role)
    line_gap = 3
    content_height = (
        name_font.get_linesize()
        + line_gap
        + score_font.get_linesize()
    )
    top = info_rect.centery - content_height // 2

    drawer.draw_text(
        screen,
        name,
        (info_rect.left, top),
        role=name_role,
        color=PALETTE.text_primary,
    )
    drawer.draw_text(
        screen,
        score_text,
        (info_rect.left, top + name_font.get_linesize() + line_gap),
        role=score_role,
        color=PALETTE.gold,
    )


def _fit_text_to_width(
    drawer: PrimitiveDrawer,
    text: str,
    *,
    max_width: int,
    role: str,
) -> str:
    """Shorten one line with an ellipsis so it stays inside its rectangle."""

    font = drawer._font_for_role(role)
    if max_width <= 0:
        return ""
    if font.size(text)[0] <= max_width:
        return text

    ellipsis = "…"
    if font.size(ellipsis)[0] > max_width:
        return ""

    low = 0
    high = len(text)
    while low < high:
        middle = (low + high + 1) // 2
        candidate = f"{text[:middle].rstrip()}{ellipsis}"
        if font.size(candidate)[0] <= max_width:
            low = middle
        else:
            high = middle - 1
    return f"{text[:low].rstrip()}{ellipsis}"


def draw_hand(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    assets: GuiAssets,
) -> None:
    """Draw the local player's hand and its optional interaction prompt."""

    hand_cards = visual_state.hand
    placements = hand_card_placements(geometry, card_count=len(hand_cards))
    target_by_value = {target.card_value: target for target in game_targets.card_targets}

    for card, placement in zip(hand_cards, placements, strict=False):
        if not card.visible:
            continue
        target = target_by_value.get(card.card_value)
        selected = card.emphasis == "selected" or (
            target is not None and target.card.selected
        )
        hovered = target.card.hovered if target is not None else False
        GuiCard(
            card_value=card.card_value,
            bullheads=card.bullheads,
            rect=placement.rect,
            selected=selected,
            hovered=hovered,
        ).draw(screen, drawer=drawer, assets=assets)

    if visual_state.status.hand_prompt is not None and placements:
        pending_rect = pygame.Rect(
            24,
            max(60, placements[0].rect.top - 42),
            270,
            34,
        )
        _draw_overlay_box(screen, pending_rect)
        drawer.draw_text(
            screen,
            visual_state.status.hand_prompt,
            (pending_rect.left + 10, pending_rect.top + 8),
            role="small",
            color=PALETTE.accent,
        )



def draw_status_overlay(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    animation_clock: AnimationClock,
) -> None:
    """Draw status text, presentation panel, and continue interaction."""

    _draw_overlay_box(screen, geometry.overlay_rect)

    drawer.draw_text(
        screen,
        visual_state.status.primary_line,
        (geometry.overlay_rect.left + 10, geometry.overlay_rect.top + 8),
        role="small",
    )
    drawer.draw_text(
        screen,
        visual_state.status.secondary_line,
        (geometry.overlay_rect.left + 10, geometry.overlay_rect.top + 30),
        role="tiny",
        color=_status_message_color(visual_state.status.message_level),
    )

    if visual_state.presentation_panel is not None:
        draw_presentation_panel(
            screen,
            drawer,
            geometry,
            visual_state.presentation_panel,
            animation_clock,
        )

    if game_targets.continue_target is not None:
        draw_button(
            screen,
            drawer,
            game_targets.continue_target.rect,
            "Weiter [Leertaste]",
            variant="primary",
            hovered=game_targets.continue_target.hovered,
            theme=THEME,
        )


def _status_message_color(level: MessageLevel) -> pygame.Color:
    if level == "error":
        return PALETTE.danger
    if level == "info":
        return PALETTE.text_primary
    return PALETTE.text_muted


def _draw_overlay_box(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_overlay_panel(screen, rect, theme=THEME)
