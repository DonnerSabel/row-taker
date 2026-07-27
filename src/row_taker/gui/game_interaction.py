from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from row_taker.client.actions import (
    ClientActionAdvancePresentation,
    ClientActionChooseCard,
    ClientActionChooseRow,
)
from row_taker.client.state import ClientState
from row_taker.engine.game import Phase
from row_taker.gui.board_layout import BoardGeometry, CardPlacement, hand_card_placements
from row_taker.gui.card import GuiCard
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult


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
    row_id: object
    rect: pygame.Rect
    hovered: bool = False


@dataclass(frozen=True, slots=True)
class ContinueTarget:
    rect: pygame.Rect
    hovered: bool = False


@dataclass(frozen=True, slots=True)
class GameScreenTargets:
    card_targets: tuple[CardTarget, ...] = ()
    row_targets: tuple[RowTarget, ...] = ()
    continue_target: ContinueTarget | None = None


def build_game_screen_targets(
    geometry: BoardGeometry,
    state: ClientState,
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
            state,
            mouse_pos=resolved_mouse_pos,
        ),
        row_targets=_build_row_targets(
            geometry,
            state,
            mouse_pos=resolved_mouse_pos,
        ),
        continue_target=_build_continue_target(
            geometry,
            state,
            mouse_pos=resolved_mouse_pos,
        ),
    )


def handle_game_event(
    event: pygame.event.Event,
    *,
    state: ClientState | None,
    game_targets: GameScreenTargets | None,
) -> ScreenResult:
    if event.type == pygame.QUIT:
        return ScreenResult(request_quit=True)

    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return ScreenResult(request_quit=True)

    if state is None or game_targets is None:
        return NO_SCREEN_RESULT

    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and state.pending_presentation_events:
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_left_click(event.pos, game_targets=game_targets)

    return NO_SCREEN_RESULT


def _handle_left_click(position: tuple[int, int], *, game_targets: GameScreenTargets) -> ScreenResult:
    # Hand cards overlap. Check front-to-back.
    for target in reversed(game_targets.card_targets):
        if target.contains_point(position):
            return ScreenResult(client_action=ClientActionChooseCard(card_value=target.card_value))

    for target in game_targets.row_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseRow(row_id=target.row_id))

    if game_targets.continue_target is not None and game_targets.continue_target.rect.collidepoint(position):
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    return NO_SCREEN_RESULT


def _build_card_targets(
    geometry: BoardGeometry,
    state: ClientState,
    *,
    mouse_pos: tuple[int, int],
) -> tuple[CardTarget, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()

    placements = hand_card_placements(geometry, card_count=len(player_state.hand))
    hovered_value = _hovered_hand_card_value(tuple(zip(player_state.hand, placements, strict=False)), mouse_pos)
    return tuple(
        CardTarget(
            card=GuiCard.from_card(
                card,
                placement.rect,
                hovered=int(card.value) == hovered_value,
            )
        )
        for card, placement in zip(player_state.hand, placements, strict=False)
    )


def _hovered_hand_card_value(
    cards_with_placements: tuple[tuple[Any, CardPlacement], ...],
    mouse_pos: tuple[int, int],
) -> int | None:
    # Hand cards overlap. Only the visually front-most card should react.
    for card, placement in reversed(cards_with_placements):
        if placement.rect.collidepoint(mouse_pos):
            return int(card.value)
    return None


def _build_row_targets(
    geometry: BoardGeometry,
    state: ClientState,
    *,
    mouse_pos: tuple[int, int],
) -> tuple[RowTarget, ...]:
    public_state = state.public_state
    player_state = state.player_state
    if public_state is None or player_state is None:
        return ()

    if player_state.phase_info.phase != Phase.CHOOSE_ROW:
        return ()

    selectable = set(player_state.get_selectable_row_ids_for_choose_row())
    targets: list[RowTarget] = []
    for row, rect in zip(public_state.rows, geometry.row_columns, strict=False):
        if row.row_id in selectable:
            targets.append(RowTarget(row_id=row.row_id, rect=rect, hovered=rect.collidepoint(mouse_pos)))
    return tuple(targets)


def _build_continue_target(
    geometry: BoardGeometry,
    state: ClientState,
    *,
    mouse_pos: tuple[int, int],
) -> ContinueTarget | None:
    if not state.pending_presentation_events:
        return None

    rect = pygame.Rect(
        geometry.stats_rect.left + 12,
        geometry.stats_rect.bottom - 46,
        max(1, geometry.stats_rect.width - 24),
        34,
    )
    return ContinueTarget(rect=rect, hovered=rect.collidepoint(mouse_pos))
