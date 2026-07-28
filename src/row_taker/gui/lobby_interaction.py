from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.actions import (
    ClientActionAssignSelfToSeat,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionStartGame,
)
from row_taker.client.state import (
    ClientState,
    UiMessage,
    clear_bot_name_editor,
    clear_flash_message,
    enter_lobby_submenu,
    select_bot_name_text,
    set_bot_name_editor,
    set_flash_message,
)
from row_taker.gui.layout import GuiLayout
from row_taker.gui.lobby_layout import compute_lobby_panel_layout, row_rects
from row_taker.gui.menu_layout import DEFAULT_MENU_LAYOUT
from row_taker.gui.screen_result import NO_SCREEN_RESULT, ScreenResult
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import LobbySeatView

MENU_LAYOUT = DEFAULT_MENU_LAYOUT


@dataclass(frozen=True, slots=True)
class SeatTarget:
    seat_index: int
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class LobbyButtonTarget:
    button_id: str
    label: str
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class LobbyScreenTargets:
    seat_targets: tuple[SeatTarget, ...] = ()
    button_targets: tuple[LobbyButtonTarget, ...] = ()
    bot_name_input_rect: pygame.Rect | None = None


def build_lobby_screen_targets(layout: GuiLayout, state: ClientState) -> LobbyScreenTargets:
    seat_targets = _build_lobby_seat_targets(layout, state)
    edited_seat_index = (
        state.navigation_state.selected_seat_index if is_editing_bot_name(state) else None
    )
    input_rect = next(
        (
            target.rect.inflate(-72, -8).move(58, 0)
            for target in seat_targets
            if target.seat_index == edited_seat_index
        ),
        None,
    )
    return LobbyScreenTargets(
        seat_targets=seat_targets,
        button_targets=_build_lobby_button_targets(layout, state),
        bot_name_input_rect=input_rect,
    )


def handle_lobby_event(
    event: pygame.event.Event,
    *,
    state: ClientState | None,
    lobby_targets: LobbyScreenTargets | None,
) -> ScreenResult:
    if event.type == pygame.QUIT:
        return ScreenResult(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        if state is not None and is_editing_bot_name(state):
            return ScreenResult(next_state=_leave_bot_name_editor(state))
        return ScreenResult(request_quit=True)
    if state is None or lobby_targets is None:
        return NO_SCREEN_RESULT
    if is_editing_bot_name(state):
        return _handle_bot_name_event(event, state=state, lobby_targets=lobby_targets)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_left_click(event.pos, state=state, lobby_targets=lobby_targets)
    return NO_SCREEN_RESULT


def _handle_left_click(
    position: tuple[int, int],
    *,
    state: ClientState,
    lobby_targets: LobbyScreenTargets,
) -> ScreenResult:
    for seat_target in lobby_targets.seat_targets:
        if seat_target.rect.collidepoint(position):
            seat = _seat_by_index(state, seat_target.seat_index)
            if seat is not None and seat.occupant_kind == ParticipantKind.BOT:
                return ScreenResult(
                    next_state=_enter_bot_name_editor(
                        state,
                        seat_target.seat_index,
                        seat.occupant_display_name,
                    )
                )
            return ScreenResult(
                next_state=enter_lobby_submenu(
                    state,
                    "seat_edit",
                    selected_seat_index=seat_target.seat_index,
                )
            )

    for button_target in lobby_targets.button_targets:
        if button_target.rect.collidepoint(position):
            return _map_lobby_button(button_target.button_id, state)

    return NO_SCREEN_RESULT


def _map_lobby_button(button_id: str, state: ClientState) -> ScreenResult:
    selected_seat_index = state.navigation_state.selected_seat_index
    if button_id == "start_game":
        return ScreenResult(client_action=ClientActionStartGame())
    if button_id == "back":
        return ScreenResult(next_state=enter_lobby_submenu(state, "main"))
    if selected_seat_index is None:
        return NO_SCREEN_RESULT
    if button_id == "take_seat":
        return ScreenResult(
            client_action=ClientActionAssignSelfToSeat(seat_index=selected_seat_index)
        )
    if button_id == "create_bot":
        seat = _seat_by_index(state, selected_seat_index)
        initial_name = None if seat is None else seat.occupant_display_name
        return ScreenResult(
            next_state=_enter_bot_name_editor(state, selected_seat_index, initial_name)
        )
    if button_id == "clear_seat":
        return ScreenResult(client_action=ClientActionClearSeat(seat_index=selected_seat_index))
    return NO_SCREEN_RESULT


def _handle_bot_name_event(
    event: pygame.event.Event,
    *,
    state: ClientState,
    lobby_targets: LobbyScreenTargets,
) -> ScreenResult:
    if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
        return _confirm_bot_name(state)
    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return _confirm_bot_name(state)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE:
        return ScreenResult(next_state=_backspace_bot_name(state))
    if event.type == pygame.KEYDOWN and event.unicode:
        return ScreenResult(next_state=_append_bot_name_character(state, event.unicode))
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if (
            lobby_targets.bot_name_input_rect is not None
            and lobby_targets.bot_name_input_rect.collidepoint(event.pos)
        ):
            return ScreenResult(next_state=select_bot_name_text(state))
        return _confirm_bot_name(state)
    return NO_SCREEN_RESULT


def _build_lobby_seat_targets(layout: GuiLayout, state: ClientState) -> tuple[SeatTarget, ...]:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return ()

    panel_layout = compute_lobby_panel_layout(layout, lobby_view.seat_count)
    rows = row_rects(panel_layout.seat_list_rect, len(lobby_view.seats))
    return tuple(
        SeatTarget(seat_index=seat.seat_index, rect=rows[index])
        for index, seat in enumerate(lobby_view.seats)
        if index < len(rows)
    )


def _build_lobby_button_targets(
    layout: GuiLayout, state: ClientState
) -> tuple[LobbyButtonTarget, ...]:
    lobby_view = state.lobby_view
    seat_count = 4 if lobby_view is None else max(1, lobby_view.seat_count)
    action_rect = compute_lobby_panel_layout(layout, seat_count).action_rect
    button_width = MENU_LAYOUT.panel_button_secondary_width
    gap = MENU_LAYOUT.button_gap
    y = action_rect.top

    buttons: list[LobbyButtonTarget] = []
    x = action_rect.left
    selected_seat_index = state.navigation_state.selected_seat_index
    selected_seat = (
        None if selected_seat_index is None else _seat_by_index(state, selected_seat_index)
    )

    if selected_seat_index is not None:
        if selected_seat is None or selected_seat.occupant_display_name is None:
            for button_id, label in (("take_seat", "Nehmen"), ("create_bot", "Bot")):
                buttons.append(
                    LobbyButtonTarget(
                        button_id,
                        label,
                        pygame.Rect(x, y, button_width, MENU_LAYOUT.control_height),
                    )
                )
                x += button_width + gap
        elif selected_seat.occupant_kind == ParticipantKind.BOT:
            for button_id, label in (("create_bot", "Name"), ("clear_seat", "Leeren")):
                buttons.append(
                    LobbyButtonTarget(
                        button_id,
                        label,
                        pygame.Rect(x, y, button_width, MENU_LAYOUT.control_height),
                    )
                )
                x += button_width + gap
        else:
            buttons.append(
                LobbyButtonTarget(
                    "clear_seat",
                    "Leeren",
                    pygame.Rect(x, y, button_width, MENU_LAYOUT.control_height),
                )
            )
            x += button_width + gap

        buttons.append(
            LobbyButtonTarget(
                "back", "Lösen", pygame.Rect(x, y, button_width, MENU_LAYOUT.control_height)
            )
        )

    start_width = MENU_LAYOUT.panel_button_width
    buttons.append(
        LobbyButtonTarget(
            button_id="start_game",
            label="Spiel starten",
            rect=pygame.Rect(
                action_rect.right - start_width, y, start_width, MENU_LAYOUT.control_height
            ),
        )
    )
    return tuple(buttons)


def is_editing_bot_name(state: ClientState) -> bool:
    return state.navigation_state.lobby_submenu == "bot_name"


def _enter_bot_name_editor(
    state: ClientState, seat_index: int, initial_name: str | None
) -> ClientState:
    next_state = enter_lobby_submenu(state, "bot_name", selected_seat_index=seat_index)
    next_state = clear_flash_message(next_state)
    return set_bot_name_editor(
        next_state,
        text=initial_name or _default_bot_name_for_seat(seat_index),
        selected=True,
    )


def _leave_bot_name_editor(state: ClientState) -> ClientState:
    selected = state.navigation_state.selected_seat_index
    return clear_bot_name_editor(
        enter_lobby_submenu(state, "seat_edit", selected_seat_index=selected)
    )


def _append_bot_name_character(state: ClientState, character: str) -> ClientState:
    if len(character) != 1 or not character.isprintable():
        return state
    current = state.navigation_state.bot_name_text
    next_text = character if state.navigation_state.bot_name_selected else current + character
    if len(next_text) > 32:
        return state
    next_state = clear_flash_message(state)
    return set_bot_name_editor(next_state, text=next_text, selected=False)


def _backspace_bot_name(state: ClientState) -> ClientState:
    current = state.navigation_state.bot_name_text
    next_text = "" if state.navigation_state.bot_name_selected else current[:-1]
    next_state = clear_flash_message(state)
    return set_bot_name_editor(next_state, text=next_text, selected=False)


def _confirm_bot_name(state: ClientState) -> ScreenResult:
    seat_index = state.navigation_state.selected_seat_index
    if seat_index is None:
        return ScreenResult(next_state=enter_lobby_submenu(state, "main"))
    name = state.navigation_state.bot_name_text.strip() or _default_bot_name_for_seat(seat_index)
    collision = _bot_name_collision(state, name=name, edited_seat_index=seat_index)
    if collision is not None:
        return ScreenResult(
            next_state=set_flash_message(
                state,
                UiMessage(level="error", text=f"Name bereits vergeben: {collision}"),
            )
        )
    return ScreenResult(client_action=ClientActionCreateBot(seat_index=seat_index, name=name))


def _bot_name_collision(state: ClientState, *, name: str, edited_seat_index: int) -> str | None:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return None
    normalized = name.casefold()
    for participant in lobby_view.participants:
        if participant.seat_index == edited_seat_index:
            continue
        if participant.display_name.casefold() == normalized:
            return participant.display_name
    for seat in lobby_view.seats:
        if seat.seat_index == edited_seat_index or seat.occupant_display_name is None:
            continue
        if seat.occupant_display_name.casefold() == normalized:
            return seat.occupant_display_name
    return None


def default_bot_name(state: ClientState) -> str:
    seat_index = state.navigation_state.selected_seat_index
    return "Bot" if seat_index is None else _default_bot_name_for_seat(seat_index)


def _default_bot_name_for_seat(seat_index: int) -> str:
    return f"Bot_{seat_index + 1}"


def _seat_by_index(state: ClientState, seat_index: int) -> LobbySeatView | None:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return None
    for seat in lobby_view.seats:
        if seat.seat_index == seat_index:
            return seat
    return None


__all__ = [
    "LobbyButtonTarget",
    "LobbyScreenTargets",
    "SeatTarget",
    "build_lobby_screen_targets",
    "default_bot_name",
    "handle_lobby_event",
    "is_editing_bot_name",
]
