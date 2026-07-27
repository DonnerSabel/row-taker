from __future__ import annotations

from collections.abc import Mapping

import pygame

from row_taker.engine.game.models import PlayerID
from row_taker.gui.animation import AnimationClock
from row_taker.gui.assets import GuiAssets
from row_taker.gui.board_layout import BoardGeometry, hand_card_placements
from row_taker.gui.card import GuiCard, draw_card_back
from row_taker.gui.game_interaction import GameScreenTargets
from row_taker.gui.game_visual_state import GameVisualState, MessageLevel
from row_taker.gui.presentation_renderer import draw_presentation_panel
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_button, draw_overlay_panel

THEME = DEFAULT_THEME
PALETTE = THEME.palette


def opponent_staged_card_rects(
    visual_state: GameVisualState,
    geometry: BoardGeometry,
) -> Mapping[PlayerID, pygame.Rect]:
    """Map semantic opponent ids to their prepared staged-card rectangles."""

    return {
        player.player_id: slot_geometry.staged_card.rect
        for player, slot_geometry in zip(
            visual_state.opponents,
            geometry.opponent_slots,
            strict=False,
        )
    }


def draw_opponent_slots(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    """Draw opponent portraits and their current staged cards."""

    for index, (player, slot_geometry) in enumerate(
        zip(visual_state.opponents, geometry.opponent_slots, strict=False)
    ):
        color = _player_color(index)
        circle_rect = slot_geometry.circle_rect
        active_player = player.emphasis == "active"
        pygame.draw.ellipse(screen, color, circle_rect)
        pygame.draw.ellipse(
            screen,
            pygame.Color(255, 255, 255, 150),
            circle_rect,
            2,
        )
        if active_player:
            inflate = 8 + animation_clock.pulse_inflate(
                period_frames=54,
                max_pixels=8,
            )
            ring_color = animation_clock.pulsed_color(
                PALETTE.accent,
                PALETTE.accent_hover,
                period_frames=54,
            )
            pygame.draw.ellipse(
                screen,
                ring_color,
                circle_rect.inflate(inflate, inflate),
                3,
            )

        drawer.draw_text(
            screen,
            _initials(player.name),
            (circle_rect.centerx - 8, circle_rect.centery - 8),
            role="tiny",
            color=PALETTE.text_primary,
        )

        staged_rect = slot_geometry.staged_card.rect
        if player.staged_card_value is None:
            draw_card_back(screen, staged_rect)
        else:
            GuiCard.from_card_value(
                player.staged_card_value,
                staged_rect,
                selected=active_player,
            ).draw(screen, drawer=drawer, assets=assets)


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


def draw_stats_field(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
) -> None:
    """Draw the local score summary and compact player score list."""

    rect = geometry.stats_rect
    draw_overlay_panel(screen, rect, radius=12, alpha=35, theme=THEME)

    own_player = visual_state.own_player
    own_score = str(own_player.score) if own_player is not None else "-"
    own_name = own_player.name if own_player is not None else "-"

    drawer.draw_text(
        screen,
        own_name,
        (rect.left + 12, rect.top + 14),
        role="small",
        color=PALETTE.text_muted,
    )
    drawer.draw_text(
        screen,
        "Hornochsen",
        (rect.left + 12, rect.top + 42),
        role="small",
        color=PALETTE.text_muted,
    )
    drawer.draw_text(
        screen,
        own_score,
        (rect.left + 12, rect.top + 66),
        role="title",
        color=PALETTE.accent,
    )

    y = rect.top + 112
    for player in visual_state.players:
        marker = "★ " if player.is_self else ""
        drawer.draw_text(
            screen,
            f"{marker}{player.name}: {player.score}",
            (rect.left + 12, y),
            role="tiny",
            color=PALETTE.text_primary if player.is_self else PALETTE.text_muted,
        )
        y += 20
        if y > rect.bottom - 54:
            break


def draw_status_overlay(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    assets: GuiAssets,
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
            assets,
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


def _initials(name: str) -> str:
    parts = [part for part in name.strip().split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[-1][0]}".upper()


def _player_color(index: int) -> pygame.Color:
    colors = (
        pygame.Color(216, 83, 83),
        pygame.Color(83, 151, 216),
        pygame.Color(237, 194, 76),
        pygame.Color(122, 197, 104),
        pygame.Color(177, 113, 219),
    )
    return colors[index % len(colors)]
