from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.actions import (
    ClientActionAdvancePresentation,
    ClientActionChooseCard,
    ClientActionChooseRow,
)
from row_taker.engine.game.models import RowID
from row_taker.gui.board_layout import BoardGeometry, CardPlacement, hand_card_placements
from row_taker.gui.card import GuiCard
from row_taker.gui.game_visual_state import GameVisualState, VisualHandCard
from row_taker.gui.screen_result import NO_SCREEN_RESULT, ScreenResult


@dataclass(frozen=True, slots=True)
class CardTarget:
    card: GuiCard

    @property
    def card_value(self) -> int:
        return self.card.card_value

    @property
    def rect(self) -> pygame.Rect:
        return self.card.rect

    def contains_point(self, position: tuple[int, int]) -> bool:
        return self.card.contains_point(position)


@dataclass(frozen=True, slots=True)
class RowTarget:
    row_id: RowID
    rect: pygame.Rect
    hovered: bool = False


@dataclass(frozen=True, slots=True)
class GameScreenTargets:
    card_targets: tuple[CardTarget, ...] = ()
    row_targets: tuple[RowTarget, ...] = ()


def build_game_screen_targets(
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    *,
    mouse_pos: tuple[int, int] | None = None,
) -> GameScreenTargets:
    """Build all interactive targets for one game frame.

    The live GUI leaves ``mouse_pos`` unset and therefore uses the real pygame
    pointer position. Deterministic hosts such as the GUI workbench pass an
    explicit position while still using this exact production function.
    """

    resolved_mouse_pos = pygame.mouse.get_pos() if mouse_pos is None else mouse_pos
    return GameScreenTargets(
        card_targets=_build_card_targets(
            geometry,
            visual_state,
            mouse_pos=resolved_mouse_pos,
        ),
        row_targets=_build_row_targets(
            geometry,
            visual_state,
            mouse_pos=resolved_mouse_pos,
        ),
    )


def handle_game_event(
    event: pygame.event.Event,
    *,
    visual_state: GameVisualState | None,
    game_targets: GameScreenTargets | None,
) -> ScreenResult:
    if event.type == pygame.QUIT:
        return ScreenResult(request_quit=True)

    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return ScreenResult(request_quit=True)

    if visual_state is None or game_targets is None:
        return NO_SCREEN_RESULT

    if (
        event.type == pygame.MOUSEBUTTONDOWN
        and event.button in (1, 3)
        and visual_state.interaction.can_advance_presentation
    ):
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_left_click(event.pos, game_targets=game_targets)

    return NO_SCREEN_RESULT


def _handle_left_click(
    position: tuple[int, int],
    *,
    game_targets: GameScreenTargets,
) -> ScreenResult:
    # Hand cards overlap. Check front-to-back.
    for target in reversed(game_targets.card_targets):
        if target.contains_point(position):
            return ScreenResult(client_action=ClientActionChooseCard(card_value=target.card_value))

    for target in game_targets.row_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseRow(row_id=target.row_id))

    return NO_SCREEN_RESULT


def _build_card_targets(
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    *,
    mouse_pos: tuple[int, int],
) -> tuple[CardTarget, ...]:
    cards = visual_state.hand
    placements = hand_card_placements(geometry, card_count=len(cards))
    selectable = visual_state.interaction.selectable_card_values
    selectable_cards_with_placements = tuple(
        (card, placement)
        for card, placement in zip(cards, placements, strict=False)
        if card.visible and card.card_value in selectable
    )
    hovered_value = _hovered_hand_card_value(selectable_cards_with_placements, mouse_pos)
    return tuple(
        CardTarget(
            card=GuiCard(
                card_value=card.card_value,
                bullheads=card.bullheads,
                rect=placement.rect,
                hovered=card.card_value == hovered_value,
            )
        )
        for card, placement in selectable_cards_with_placements
    )


def _hovered_hand_card_value(
    cards_with_placements: tuple[tuple[VisualHandCard, CardPlacement], ...],
    mouse_pos: tuple[int, int],
) -> int | None:
    # Hand cards overlap. Only the visually front-most selectable card reacts.
    for card, placement in reversed(cards_with_placements):
        if placement.rect.collidepoint(mouse_pos):
            return card.card_value
    return None


def _build_row_targets(
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    *,
    mouse_pos: tuple[int, int],
) -> tuple[RowTarget, ...]:
    selectable = visual_state.interaction.selectable_row_ids
    return tuple(
        RowTarget(
            row_id=row.row_id,
            rect=rect,
            hovered=rect.collidepoint(mouse_pos),
        )
        for row, rect in zip(visual_state.rows, geometry.row_columns, strict=False)
        if row.row_id in selectable
    )
