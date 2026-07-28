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
from row_taker.gui.widgets import draw_overlay_panel, draw_panel

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
    prepared = tuple(zip(opponents, geometry.opponent_tiles, strict=False))

    # Draw all tile backgrounds first. Cards are a separate layer because
    # neighbouring cards may intentionally overlap vertically.
    for player, tile in prepared:
        _draw_player_tile_background(
            screen,
            tile.tile_rect,
            active=player.emphasis == "active",
        )

    # Draw inactive staged cards in player order, then active cards once more
    # on top. The cards intentionally overlap vertically, so an active card
    # must not lose its highlight behind a neighbouring card.
    for active_layer in (False, True):
        for player, tile in prepared:
            active = player.emphasis == "active"
            if active != active_layer or player.staged_card_value is None:
                continue
            _draw_staged_card(
                screen,
                drawer,
                assets,
                card_value=player.staged_card_value,
                card_rect=tile.card_placement.rect,
                active=active,
            )

    for player, tile in prepared:
        active = player.emphasis == "active"
        _draw_player_tile_text(
            screen,
            drawer,
            info_rect=tile.info_rect,
            player_name=player.name,
            score=player.score,
            active=active,
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
    active = player.emphasis == "active"
    _draw_player_tile_background(screen, tile.tile_rect, active=active)
    if player.staged_card_value is not None:
        _draw_staged_card(
            screen,
            drawer,
            assets,
            card_value=player.staged_card_value,
            card_rect=tile.card_placement.rect,
            active=active,
        )
    _draw_player_tile_text(
        screen,
        drawer,
        info_rect=tile.info_rect,
        player_name=player.name,
        score=player.score,
        active=active,
        status_line=visual_state.status.action_line,
    )


def _draw_player_tile_background(
    screen: pygame.Surface,
    tile_rect: pygame.Rect,
    *,
    active: bool,
) -> None:
    draw_panel(
        screen,
        tile_rect.inflate(-2, -4),
        radius=8,
        fill=PALETTE.panel_fill if active else PALETTE.panel_fill_soft,
        border=(PALETTE.panel_border_active if active else PALETTE.panel_border),
        border_width=3 if active else 1,
        alpha=220 if active else 150,
        theme=THEME,
    )


def _draw_staged_card(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    assets: GuiAssets,
    *,
    card_value: int,
    card_rect: pygame.Rect,
    active: bool,
) -> None:
    GuiCard.from_card_value(
        card_value,
        card_rect,
        selected=active,
    ).draw(
        screen,
        drawer=drawer,
        assets=assets,
    )


def _draw_player_tile_text(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    *,
    info_rect: pygame.Rect,
    player_name: str,
    score: int,
    active: bool,
    status_line: str | None = None,
) -> None:
    name_role = "small"
    score_role = "tiny"
    status_role = "tiny"
    name = _fit_text_to_width(
        drawer,
        player_name,
        max_width=info_rect.width,
        role=name_role,
    )
    score_text = f"{score} Hornochsen"
    fitted_status = (
        _fit_text_to_width(
            drawer,
            status_line,
            max_width=info_rect.width,
            role=status_role,
        )
        if status_line is not None
        else None
    )

    name_font = drawer._font_for_role(name_role)
    score_font = drawer._font_for_role(score_role)
    status_font = drawer._font_for_role(status_role)
    line_gap = 3
    content_height = name_font.get_linesize() + line_gap + score_font.get_linesize()
    if fitted_status:
        content_height += line_gap + status_font.get_linesize()
    top = info_rect.centery - content_height // 2

    drawer.draw_text(
        screen,
        name,
        (info_rect.left, top),
        role=name_role,
        color=PALETTE.accent_hover if active else PALETTE.text_primary,
    )
    score_top = top + name_font.get_linesize() + line_gap
    drawer.draw_text(
        screen,
        score_text,
        (info_rect.left, score_top),
        role=score_role,
        color=PALETTE.gold,
    )
    if fitted_status:
        drawer.draw_text(
            screen,
            fitted_status,
            (info_rect.left, score_top + score_font.get_linesize() + line_gap),
            role=status_role,
            color=PALETTE.accent,
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
        selected = card.emphasis == "selected" or (target is not None and target.card.selected)
        hovered = target.card.hovered if target is not None else False
        GuiCard(
            card_value=card.card_value,
            bullheads=card.bullheads,
            rect=placement.rect,
            selected=selected,
            hovered=hovered,
        ).draw(screen, drawer=drawer, assets=assets)


def draw_sidebar_status(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    animation_clock: AnimationClock,
) -> None:
    """Draw the final readable status layer inside the new sidebar."""

    _draw_sidebar_header(screen, drawer, geometry, visual_state)

    if visual_state.presentation_panel is not None:
        draw_presentation_panel(
            screen,
            drawer,
            geometry.presentation_rect,
            visual_state.presentation_panel,
            animation_clock,
        )
    else:
        _draw_sidebar_message(
            screen,
            drawer,
            geometry.presentation_rect,
            visual_state.status.message_line,
            visual_state.status.message_level,
        )


def _draw_sidebar_header(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
) -> None:
    rect = geometry.sidebar_header_rect
    _draw_overlay_box(screen, rect)
    font = drawer._font_for_role("small")
    text_y = rect.centery - font.get_linesize() // 2
    drawer.draw_text(
        screen,
        visual_state.status.game_line,
        (rect.left + 12, text_y),
        role="small",
        color=PALETTE.text_primary,
    )


def _draw_sidebar_message(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    message: str | None,
    level: MessageLevel,
) -> None:
    _draw_overlay_box(screen, rect)
    if not message:
        return

    content_rect = pygame.Rect(
        rect.left + 12,
        rect.top + 10,
        max(1, rect.width - 24),
        max(1, rect.height - 20),
    )
    drawer.draw_wrapped_lines(
        screen,
        (message,),
        content_rect,
        role="tiny",
        color=_status_message_color(level),
    )


def _status_message_color(level: MessageLevel) -> pygame.Color:
    if level == "error":
        return PALETTE.danger
    if level == "info":
        return PALETTE.text_primary
    return PALETTE.text_muted


def _draw_overlay_box(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_overlay_panel(screen, rect, theme=THEME)
