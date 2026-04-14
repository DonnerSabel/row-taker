from __future__ import annotations

from dataclasses import dataclass, replace

from row_taker.cli.row_display import build_row_display_mapping
from row_taker.cli.state_models import (
    CliFeedbackState,
    CliNavigationState,
    CliState,
    UiMessage,
    apply_feedback_state,
    apply_navigation_state,
)
from row_taker.client.actions import (
    UiAction,
    UiActionAdvancePresentation,
    UiActionAssignSelfToSeat,
    UiActionChooseCard,
    UiActionChooseRow,
    UiActionClearSeat,
    UiActionCreateBot,
    UiActionLeaveSession,
    UiActionRename,
    UiActionStartGame,
)
from row_taker.client.core_state import ClientMode, PendingAction


@dataclass(frozen=True, slots=True)
class FrontendInputResult:
    state: CliState
    action: UiAction | None = None


class CliFrontend:
    def sync_to_core(self, state: CliState) -> CliState:
        return sync_frontend_to_core(state)

    def handle_text_input(self, state: CliState, text: str) -> FrontendInputResult:
        return parse_text_to_action(state, text)

    def clear_flash(self, state: CliState) -> CliState:
        return clear_flash(state)



def sync_frontend_to_core(state: CliState) -> CliState:
    core = state.core_state

    if core.client_mode == ClientMode.LOBBY:
        return state

    return apply_navigation_state(state, CliNavigationState())



def set_flash(state: CliState, level: str, text: str) -> CliState:
    return apply_feedback_state(state, replace(state.feedback_state, flash_message=UiMessage(level=level, text=text)))



def clear_flash(state: CliState) -> CliState:
    return apply_feedback_state(state, replace(state.feedback_state, flash_message=None))



def mark_server_error(state: CliState) -> CliState:
    return apply_feedback_state(
        state,
        replace(state.feedback_state, exit_on_ack=True, suppress_final_result=True, flash_message=None),
    )



def mark_session_ended(state: CliState) -> CliState:
    return apply_feedback_state(
        state,
        replace(state.feedback_state, exit_on_ack=False, suppress_final_result=True, should_exit=True, flash_message=None),
    )



def mark_leave_requested(state: CliState) -> CliState:
    return apply_feedback_state(
        state,
        replace(state.feedback_state, should_exit=True, suppress_final_result=True, flash_message=None),
    )



def acknowledge_session_error(state: CliState, text: str) -> FrontendInputResult:
    if state.session_error is None:
        return FrontendInputResult(state=state)
    if not state.exit_on_ack:
        return FrontendInputResult(state=apply_feedback_state(state, replace(state.feedback_state, should_exit=True)))
    if text != "":
        return FrontendInputResult(state=state)
    return FrontendInputResult(state=apply_feedback_state(state, replace(state.feedback_state, should_exit=True)))



def parse_text_to_action(state: CliState, text: str) -> FrontendInputResult:
    normalized = text.strip()

    if normalized == "X":
        return FrontendInputResult(state=mark_leave_requested(state), action=UiActionLeaveSession())

    if state.session_error is not None:
        return acknowledge_session_error(state, normalized)

    if state.pending_presentation_events:
        if normalized == "":
            return FrontendInputResult(state=state, action=UiActionAdvancePresentation())
        return FrontendInputResult(state=set_flash(state, "info", "Bitte zuerst die lokale Auflösung mit Enter weiterführen."))

    if state.client_mode == ClientMode.LOBBY:
        return _parse_lobby_input(state, normalized)
    return _parse_game_input(state, normalized)



def _parse_lobby_input(state: CliState, normalized: str) -> FrontendInputResult:
    submenu = state.navigation_state.lobby_submenu
    seat_index = state.navigation_state.selected_seat_index

    if submenu == "main":
        return _parse_lobby_main(state, normalized)
    if submenu == "rename":
        if normalized == "":
            return FrontendInputResult(state=set_flash(state, "error", "Der Anzeigename darf nicht leer sein."))
        return FrontendInputResult(state=clear_flash(_set_lobby_submenu(state, "main")), action=UiActionRename(normalized))
    if submenu == "seat_edit":
        if seat_index is None:
            raise TypeError("seat_edit submenu requires seat_index")
        return _parse_lobby_seat_edit(state, normalized, seat_index)
    if submenu == "bot_name":
        if seat_index is None:
            raise TypeError("bot_name submenu requires seat_index")
        return _parse_lobby_bot_name(state, normalized, seat_index)
    raise ValueError(f"unsupported lobby submenu: {submenu!r}")



def _parse_game_input(state: CliState, normalized: str) -> FrontendInputResult:
    if state.client_mode == ClientMode.ENDED:
        if normalized != "":
            return FrontendInputResult(state=state)
        return FrontendInputResult(state=apply_feedback_state(state, replace(state.feedback_state, should_exit=True)))

    if state.pending_action == PendingAction.CHOOSE_CARD:
        if normalized == "":
            return FrontendInputResult(state=set_flash(state, "error", "Bitte einen Kartenwert eingeben."))
        try:
            card_value = int(normalized)
        except ValueError:
            return FrontendInputResult(state=set_flash(state, "error", "Bitte einen gültigen Kartenwert eingeben."))
        return FrontendInputResult(state=clear_flash(state), action=UiActionChooseCard(card_value))

    if state.pending_action == PendingAction.CHOOSE_ROW:
        player_state = state.player_state
        if player_state is None:
            return FrontendInputResult(state=set_flash(state, "error", "Kein Spielerzustand für Reihenwahl vorhanden."))
        row_mapping = build_row_display_mapping(player_state.public_state.rows)
        if normalized not in row_mapping:
            return FrontendInputResult(state=set_flash(state, "error", "Bitte eine gültige Reihennummer eingeben."))
        return FrontendInputResult(state=clear_flash(state), action=UiActionChooseRow(row_mapping[normalized]))

    if normalized == "":
        return FrontendInputResult(state=state)
    return FrontendInputResult(state=set_flash(state, "info", "Bitte auf den nächsten Spielschritt warten."))



def _parse_lobby_main(state: CliState, text: str) -> FrontendInputResult:
    if text == "n":
        return FrontendInputResult(state=clear_flash(_set_lobby_submenu(state, "rename")))
    if text == "g":
        return FrontendInputResult(state=clear_flash(state), action=UiActionStartGame())
    if text.isdigit():
        seat_index = int(text)
        if not _is_valid_seat_index(state, seat_index):
            return FrontendInputResult(state=set_flash(state, "error", "Ungültiger Platz."))
        return FrontendInputResult(state=clear_flash(_set_lobby_submenu(state, "seat_edit", seat_index)))
    return FrontendInputResult(state=set_flash(state, "error", "Ungültige Eingabe. Erlaubt sind n, g oder eine Platznummer."))



def _parse_lobby_seat_edit(state: CliState, text: str, seat_index: int) -> FrontendInputResult:
    if text == "m":
        return FrontendInputResult(state=clear_flash(_set_lobby_submenu(state, "main")), action=UiActionAssignSelfToSeat(seat_index))
    if text == "b":
        return FrontendInputResult(state=clear_flash(_set_lobby_submenu(state, "bot_name", seat_index)))
    if text == "c":
        return FrontendInputResult(state=clear_flash(_set_lobby_submenu(state, "main")), action=UiActionClearSeat(seat_index))
    if text == "x":
        return FrontendInputResult(state=clear_flash(_set_lobby_submenu(state, "main")))
    return FrontendInputResult(state=set_flash(state, "error", "Ungültige Eingabe. Erlaubt sind m, b, c oder x."))



def _parse_lobby_bot_name(state: CliState, text: str, seat_index: int) -> FrontendInputResult:
    if text == "x":
        return FrontendInputResult(state=clear_flash(_set_lobby_submenu(state, "seat_edit", seat_index)))
    bot_name = text or _default_bot_name(state, seat_index)
    return FrontendInputResult(
        state=clear_flash(_set_lobby_submenu(state, "main")),
        action=UiActionCreateBot(seat_index, bot_name),
    )



def _is_valid_seat_index(state: CliState, seat_index: int) -> bool:
    lobby = state.lobby_view
    if lobby is None:
        return False
    return any(seat.seat_index == seat_index for seat in lobby.seats)



def _default_bot_name(state: CliState, seat_index: int) -> str:
    lobby = state.lobby_view
    if lobby is None:
        return f"Bot {seat_index}"
    for seat in lobby.seats:
        if seat.seat_index == seat_index and seat.occupant_display_name:
            return seat.occupant_display_name
    return f"Bot {seat_index}"



def _set_lobby_submenu(state: CliState, submenu: str, seat_index: int | None = None) -> CliState:
    return apply_navigation_state(state, replace(state.navigation_state, lobby_submenu=submenu, selected_seat_index=seat_index))
