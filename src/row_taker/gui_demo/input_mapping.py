from __future__ import annotations

from dataclasses import dataclass

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
from row_taker.gui_demo.connect_screen import (
    ConnectFormState,
    ConnectScreenTargets,
    activate_field,
    activate_next_field,
    append_character,
    backspace,
)
from row_taker.gui_demo.interactions import InteractionMap


@dataclass(frozen=True, slots=True)
class GuiDemoInput:
    request_quit: bool = False
    next_state: ClientState | None = None
    client_action: object | None = None
    next_connect_form: ConnectFormState | None = None
    connect_requested: bool = False


NO_INPUT = GuiDemoInput()


def map_pygame_event(
    event: pygame.event.Event,
    *,
    state: ClientState | None,
    interaction_map: InteractionMap | None,
    connect_form: ConnectFormState | None,
    connect_targets: ConnectScreenTargets | None,
) -> GuiDemoInput:
    if event.type == pygame.QUIT:
        return GuiDemoInput(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return GuiDemoInput(request_quit=True)

    if connect_form is not None:
        return _map_connect_event(event, connect_form=connect_form, connect_targets=connect_targets)

    if state is None or interaction_map is None:
        return NO_INPUT

    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and state.pending_presentation_events:
        return GuiDemoInput(client_action=ClientActionAdvancePresentation())
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _map_session_left_click(event.pos, state=state, interaction_map=interaction_map)
    return NO_INPUT


def _map_connect_event(
    event: pygame.event.Event,
    *,
    connect_form: ConnectFormState,
    connect_targets: ConnectScreenTargets | None,
) -> GuiDemoInput:
    if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
        return GuiDemoInput(next_connect_form=activate_next_field(connect_form))
    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return GuiDemoInput(connect_requested=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
        return GuiDemoInput(next_connect_form=backspace(connect_form))
    if event.type == pygame.KEYDOWN and event.unicode:
        next_form = append_character(connect_form, event.unicode)
        if next_form is not connect_form:
            return GuiDemoInput(next_connect_form=next_form)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and connect_targets is not None:
        for target in connect_targets.field_targets:
            if target.rect.collidepoint(event.pos):
                return GuiDemoInput(next_connect_form=activate_field(connect_form, target.field_name))
        for target in connect_targets.button_targets:
            if not target.rect.collidepoint(event.pos):
                continue
            if target.button_id == "connect":
                return GuiDemoInput(connect_requested=True)
            if target.button_id == "quit":
                return GuiDemoInput(request_quit=True)
    return NO_INPUT


def _map_session_left_click(
    position: tuple[int, int],
    *,
    state: ClientState,
    interaction_map: InteractionMap,
) -> GuiDemoInput:
    for target in interaction_map.seat_targets:
        if target.rect.collidepoint(position):
            next_state = enter_lobby_submenu(state, "seat_edit", selected_seat_index=target.seat_index)
            return GuiDemoInput(next_state=next_state)

    for target in interaction_map.lobby_button_targets:
        if not target.rect.collidepoint(position):
            continue
        return _map_lobby_button(target.button_id, state)

    for target in interaction_map.card_targets:
        if target.rect.collidepoint(position):
            return GuiDemoInput(client_action=ClientActionChooseCard(card_value=target.card_value))

    for target in interaction_map.row_targets:
        if target.rect.collidepoint(position):
            return GuiDemoInput(client_action=ClientActionChooseRow(row_id=target.row_id))

    if interaction_map.continue_target is not None and interaction_map.continue_target.rect.collidepoint(position):
        return GuiDemoInput(client_action=ClientActionAdvancePresentation())

    return NO_INPUT


def _map_lobby_button(button_id: str, state: ClientState) -> GuiDemoInput:
    seat_index = state.navigation_state.selected_seat_index
    if button_id == "start_game":
        return GuiDemoInput(client_action=ClientActionStartGame())
    if button_id == "back":
        return GuiDemoInput(next_state=enter_lobby_submenu(state, "main"))
    if seat_index is None:
        return NO_INPUT
    if button_id == "take_seat":
        return GuiDemoInput(client_action=ClientActionAssignSelfToSeat(seat_index=seat_index))
    if button_id == "create_bot":
        return GuiDemoInput(client_action=ClientActionCreateBot(seat_index=seat_index, name=f"Bot_{seat_index + 1}"))
    if button_id == "clear_seat":
        return GuiDemoInput(client_action=ClientActionClearSeat(seat_index=seat_index))
    return NO_INPUT
