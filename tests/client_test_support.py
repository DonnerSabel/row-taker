from __future__ import annotations

import random

from row_taker.cli.frontend import CliFrontend, set_flash
from row_taker.client.core_reducer import reduce_server_message as direct_reduce_server_message
from row_taker.client.game_client_core import GameClientCore
from row_taker.client.state import (
    ClientState,
    clear_flash_message,
    enter_ended_mode,
    enter_game_mode,
    enter_lobby_submenu,
)
from row_taker.engine.game import build_player_state, setup_game

_FRONTEND = CliFrontend()


def player_state_for(index: int):
    game = setup_game(["A", "B"], rng=random.Random(123))
    player_id = game.players[index].player_id
    return build_player_state(game, player_id)


def apply_server_message(state: ClientState, message) -> ClientState:
    from row_taker.protocol.messages import ChooseCardRequested, RowChoiceCommitted

    if isinstance(message, (RowChoiceCommitted, ChooseCardRequested)):
        return direct_reduce_server_message(state, message)
    core = GameClientCore(state)
    core.on_server_message(message)
    return core.state


def apply_user_input(state: ClientState, text: str):
    previous_submenu = state.navigation_state.lobby_submenu
    previous_seat_index = state.navigation_state.selected_seat_index
    previous_mode = state.client_mode
    previous_action = state.pending_action
    parsed = _FRONTEND.handle_text_input(state, text)
    state = parsed.state
    if parsed.action is None:
        return state, None
    core = GameClientCore(state)
    update = core.on_ui_action(parsed.action)
    state = core.state
    if update.local_messages:
        state = clear_flash_message(state)
        if previous_mode.value == "lobby":
            state = enter_lobby_submenu(state, previous_submenu, seat_index=previous_seat_index)
        elif previous_mode.value == "ended":
            state = enter_ended_mode(state, player_state=state.player_state)
        else:
            state = enter_game_mode(
                state, pending_action=previous_action, player_state=state.player_state
            )
        state = set_flash(state, "error", update.local_messages[-1])
        return state, None
    outbound = update.outbound_messages[0] if update.outbound_messages else None
    return state, outbound
