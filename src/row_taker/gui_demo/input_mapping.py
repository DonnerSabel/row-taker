from __future__ import annotations

import pygame

from row_taker.client.actions import (
    ClientActionAdvancePresentation,
    ClientActionAssignSelfToSeat,
    ClientActionChooseCard,
    ClientActionChooseRow,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionStartGame,
)
from row_taker.client.state import ClientState, enter_lobby_submenu
from row_taker.gui_demo.interactions import InteractionMap
from row_taker.gui_demo.ui.screen_result import NO_SCREEN_RESULT, ScreenResult


GuiDemoInput = ScreenResult
NO_INPUT = NO_SCREEN_RESULT


def map_pygame_event(
    event: pygame.event.Event,
    *,
    state: ClientState | None,
    interaction_map: InteractionMap | None,
) -> ScreenResult:
    if event.type == pygame.QUIT:
        return ScreenResult(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return ScreenResult(request_quit=True)

    if state is None or interaction_map is None:
        return NO_INPUT

    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and state.pending_presentation_events:
        return ScreenResult(client_action=ClientActionAdvancePresentation())
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _map_session_left_click(event.pos, state=state, interaction_map=interaction_map)
    return NO_INPUT


def _map_session_left_click(
    position: tuple[int, int],
    *,
    state: ClientState,
    interaction_map: InteractionMap,
) -> ScreenResult:
    for target in interaction_map.seat_targets:
        if target.rect.collidepoint(position):
            next_state = enter_lobby_submenu(state, 'seat_edit', selected_seat_index=target.seat_index)
            return ScreenResult(next_state=next_state)

    for target in interaction_map.lobby_button_targets:
        if not target.rect.collidepoint(position):
            continue
        return _map_lobby_button(target.button_id, state)

    for target in interaction_map.card_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseCard(card_value=target.card_value))

    for target in interaction_map.row_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseRow(row_id=target.row_id))

    if interaction_map.continue_target is not None and interaction_map.continue_target.rect.collidepoint(position):
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    return NO_INPUT


def _map_lobby_button(button_id: str, state: ClientState) -> ScreenResult:
    seat_index = state.navigation_state.selected_seat_index
    if button_id == 'start_game':
        return ScreenResult(client_action=ClientActionStartGame())
    if button_id == 'back':
        return ScreenResult(next_state=enter_lobby_submenu(state, 'main'))
    if seat_index is None:
        return NO_INPUT
    if button_id == 'take_seat':
        return ScreenResult(client_action=ClientActionAssignSelfToSeat(seat_index=seat_index))
    if button_id == 'create_bot':
        return ScreenResult(client_action=ClientActionCreateBot(seat_index=seat_index, name=f'Bot_{seat_index + 1}'))
    if button_id == 'clear_seat':
        return ScreenResult(client_action=ClientActionClearSeat(seat_index=seat_index))
    return NO_INPUT
