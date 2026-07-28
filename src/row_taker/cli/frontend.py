from __future__ import annotations

from dataclasses import dataclass

from row_taker.cli.row_display import build_row_display_mapping
from row_taker.client.actions import (
    ClientActionAdvancePresentation,
    ClientActionAssignSelfToSeat,
    ClientActionChooseCard,
    ClientActionChooseRow,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionLeaveSession,
    ClientActionRename,
    ClientActionStartGame,
)
from row_taker.client.core_state import ClientMode, PendingAction
from row_taker.client.state import (
    ClientState,
    UiMessage,
    UiMessageLevel,
    clear_flash_message,
    enter_lobby_submenu,
    has_pending_presentation,
    request_exit,
    set_flash_message,
)


@dataclass(frozen=True, slots=True)
class FrontendInputResult:
    state: ClientState
    action: object | None = None


class CliFrontend:
    def handle_text_input(self, state: ClientState, text: str) -> FrontendInputResult:
        return parse_text_to_action(state, text)

    def clear_flash(self, state: ClientState) -> ClientState:
        return clear_flash(state)


def set_flash(state: ClientState, level: UiMessageLevel, text: str) -> ClientState:
    return set_flash_message(state, UiMessage(level=level, text=text))


def clear_flash(state: ClientState) -> ClientState:
    return clear_flash_message(state)


def parse_text_to_action(state: ClientState, text: str) -> FrontendInputResult:
    normalized = text.strip()

    if normalized == "X":
        return FrontendInputResult(
            state=request_exit(state, suppress_final_result=True),
            action=ClientActionLeaveSession(),
        )

    if state.session_error is not None:
        if not state.exit_on_ack:
            return FrontendInputResult(state=request_exit(state))
        if normalized == "":
            return FrontendInputResult(state=request_exit(state))
        return FrontendInputResult(state=state)

    if has_pending_presentation(state):
        if normalized == "":
            return FrontendInputResult(state=state, action=ClientActionAdvancePresentation())
        return FrontendInputResult(state=set_flash(state, "info", "Bitte zuerst die lokale Auflösung mit Enter weiterführen."))

    if state.client_mode == ClientMode.LOBBY:
        return _parse_lobby_input(state, normalized)
    if state.client_mode == ClientMode.ENDED:
        if normalized == "":
            return FrontendInputResult(state=request_exit(state))
        return FrontendInputResult(state=state)
    if state.pending_action == PendingAction.CHOOSE_CARD:
        return _parse_game_choose_card(state, normalized)
    if state.pending_action == PendingAction.CHOOSE_ROW:
        return _parse_game_choose_row(state, normalized)
    return FrontendInputResult(state=state)


def _parse_lobby_input(state: ClientState, text: str) -> FrontendInputResult:
    submenu = state.navigation_state.lobby_submenu
    if submenu == "main":
        return _parse_lobby_main(state, text)
    if submenu == "rename":
        return _parse_lobby_rename(state, text)
    if submenu == "seat_edit":
        return _parse_lobby_seat_edit(state, text, state.navigation_state.selected_seat_index)
    if submenu == "bot_name":
        return _parse_lobby_bot_name(state, text, state.navigation_state.selected_seat_index)
    raise TypeError(f"unsupported lobby submenu: {submenu!r}")


def _parse_lobby_main(state: ClientState, text: str) -> FrontendInputResult:
    if text == "n":
        next_state = enter_lobby_submenu(state, "rename")
        next_state = clear_flash_message(next_state)
        return FrontendInputResult(state=next_state)
    if text == "g":
        return FrontendInputResult(state=clear_flash(state), action=ClientActionStartGame())
    if text.isdigit():
        seat_index = int(text)
        if state.lobby_view is None or not (0 <= seat_index < state.lobby_view.seat_count):
            return FrontendInputResult(state=set_flash(enter_lobby_submenu(state, "main"), "error", "Ungültiger Platz."))
        next_state = enter_lobby_submenu(state, "seat_edit", selected_seat_index=seat_index)
        next_state = clear_flash_message(next_state)
        return FrontendInputResult(state=next_state)
    return FrontendInputResult(state=set_flash(enter_lobby_submenu(state, "main"), "error", "Ungültige Eingabe. Erlaubt sind n, g oder eine Platznummer."))


def _parse_lobby_rename(state: ClientState, text: str) -> FrontendInputResult:
    if text == "":
        return FrontendInputResult(state=set_flash(enter_lobby_submenu(state, "rename"), "error", "Der Anzeigename darf nicht leer sein."))
    next_state = enter_lobby_submenu(state, "main")
    next_state = clear_flash_message(next_state)
    return FrontendInputResult(state=next_state, action=ClientActionRename(text))


def _parse_lobby_seat_edit(state: ClientState, text: str, seat_index: int | None) -> FrontendInputResult:
    if seat_index is None:
        raise TypeError("seat_edit screen requires seat_index")
    if text == "m":
        return FrontendInputResult(state=clear_flash(state), action=ClientActionAssignSelfToSeat(seat_index))
    if text == "b":
        next_state = enter_lobby_submenu(state, "bot_name", selected_seat_index=seat_index)
        next_state = clear_flash_message(next_state)
        return FrontendInputResult(state=next_state)
    if text == "c":
        return FrontendInputResult(state=clear_flash(state), action=ClientActionClearSeat(seat_index))
    if text == "x":
        next_state = enter_lobby_submenu(state, "main")
        next_state = clear_flash_message(next_state)
        return FrontendInputResult(state=next_state)
    return FrontendInputResult(state=set_flash(enter_lobby_submenu(state, "seat_edit", selected_seat_index=seat_index), "error", "Ungültige Eingabe. Erlaubt sind m, b, c oder x."))


def _parse_lobby_bot_name(state: ClientState, text: str, seat_index: int | None) -> FrontendInputResult:
    if seat_index is None:
        raise TypeError("bot_name screen requires seat_index")
    if text == "x":
        next_state = enter_lobby_submenu(state, "seat_edit", selected_seat_index=seat_index)
        next_state = clear_flash_message(next_state)
        return FrontendInputResult(state=next_state)
    display_name = text or f"Bot_{seat_index}"
    next_state = enter_lobby_submenu(state, "main")
    next_state = clear_flash_message(next_state)
    return FrontendInputResult(state=next_state, action=ClientActionCreateBot(seat_index, display_name))


def _parse_game_choose_card(state: ClientState, text: str) -> FrontendInputResult:
    try:
        value = int(text)
    except ValueError:
        return FrontendInputResult(state=set_flash(state, "error", "Bitte eine Kartenzahl eingeben."))
    return FrontendInputResult(state=clear_flash(state), action=ClientActionChooseCard(value))


def _parse_game_choose_row(state: ClientState, text: str) -> FrontendInputResult:
    player_state = state.player_state
    if player_state is None:
        raise TypeError("expected choose_row state with player_state")
    try:
        cli_row = int(text)
    except ValueError:
        return FrontendInputResult(state=set_flash(state, "error", "Bitte eine Reihennummer eingeben."))
    mapping = build_row_display_mapping(player_state.public_state)
    if cli_row < 1 or cli_row > mapping.max_cli_row():
        return FrontendInputResult(state=set_flash(state, "error", "Ungültige Reihennummer."))
    row_id = player_state.public_state.rows[mapping.to_state_index(cli_row)].row_id
    return FrontendInputResult(state=clear_flash(state), action=ClientActionChooseRow(row_id))
