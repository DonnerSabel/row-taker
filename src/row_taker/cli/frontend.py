from __future__ import annotations

from dataclasses import dataclass, replace

from row_taker.cli.row_display import build_row_display_mapping
from row_taker.cli.state_models import CliFrontendState, CliState, GameScreen, LobbyScreen, UiMessage, apply_frontend_state
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



def sync_frontend_to_core(state: CliState) -> CliState:
    core = state.core_state
    frontend = state.frontend_state

    if core.client_mode == ClientMode.LOBBY:
        if isinstance(frontend.screen, LobbyScreen):
            return apply_frontend_state(state, replace(frontend, flash_message=frontend.flash_message))
        return apply_frontend_state(state, replace(frontend, screen=LobbyScreen(kind="main")))

    if core.client_mode == ClientMode.ENDED:
        return apply_frontend_state(state, replace(frontend, screen=GameScreen(kind="ended")))

    if core.pending_action == PendingAction.CHOOSE_CARD:
        return apply_frontend_state(
            state,
            replace(frontend, screen=GameScreen(kind="choose_card", player_state=core.player_state)),
        )
    if core.pending_action == PendingAction.CHOOSE_ROW:
        return apply_frontend_state(
            state,
            replace(frontend, screen=GameScreen(kind="choose_row", player_state=core.player_state)),
        )
    return apply_frontend_state(state, replace(frontend, screen=GameScreen(kind="waiting", player_state=core.player_state)))



def set_flash(state: CliState, level: str, text: str) -> CliState:
    return apply_frontend_state(state, replace(state.frontend_state, flash_message=UiMessage(level=level, text=text)))



def clear_flash(state: CliState) -> CliState:
    return apply_frontend_state(state, replace(state.frontend_state, flash_message=None))



def mark_server_error(state: CliState) -> CliState:
    return apply_frontend_state(
        state,
        replace(state.frontend_state, exit_on_ack=True, suppress_final_result=True, flash_message=None),
    )



def mark_session_ended(state: CliState) -> CliState:
    return apply_frontend_state(
        state,
        replace(state.frontend_state, exit_on_ack=False, suppress_final_result=True, should_exit=True, flash_message=None),
    )



def mark_leave_requested(state: CliState) -> CliState:
    return apply_frontend_state(
        state,
        replace(state.frontend_state, should_exit=True, suppress_final_result=True, flash_message=None),
    )



def acknowledge_session_error(state: CliState, text: str) -> FrontendInputResult:
    if state.session_error is None:
        return FrontendInputResult(state=state)
    if not state.exit_on_ack:
        return FrontendInputResult(state=apply_frontend_state(state, replace(state.frontend_state, should_exit=True)))
    if text != "":
        return FrontendInputResult(state=state)
    return FrontendInputResult(state=apply_frontend_state(state, replace(state.frontend_state, should_exit=True)))



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

    screen = state.screen
    match screen:
        case LobbyScreen(kind="main"):
            return _parse_lobby_main(state, normalized)
        case LobbyScreen(kind="rename"):
            if normalized == "":
                return FrontendInputResult(state=set_flash(state, "error", "Der Anzeigename darf nicht leer sein."))
            return FrontendInputResult(state=clear_flash(_set_screen(state, LobbyScreen(kind="main"))), action=UiActionRename(normalized))
        case LobbyScreen(kind="seat_edit", seat_index=seat_index):
            if seat_index is None:
                raise TypeError("seat_edit screen requires seat_index")
            return _parse_lobby_seat_edit(state, normalized, seat_index)
        case LobbyScreen(kind="bot_name", seat_index=seat_index):
            if seat_index is None:
                raise TypeError("bot_name screen requires seat_index")
            return _parse_lobby_bot_name(state, normalized, seat_index)
        case GameScreen(kind="waiting"):
            if normalized == "":
                return FrontendInputResult(state=state)
            return FrontendInputResult(state=set_flash(state, "info", "Bitte auf den nächsten Spielschritt warten."))
        case GameScreen(kind="choose_card"):
            if normalized == "":
                return FrontendInputResult(state=set_flash(state, "error", "Bitte einen Kartenwert eingeben."))
            try:
                card_value = int(normalized)
            except ValueError:
                return FrontendInputResult(state=set_flash(state, "error", "Bitte einen gültigen Kartenwert eingeben."))
            next_state = clear_flash(_set_screen(state, GameScreen(kind="waiting", player_state=state.player_state)))
            return FrontendInputResult(state=next_state, action=UiActionChooseCard(card_value))
        case GameScreen(kind="choose_row"):
            player_state = state.player_state
            if player_state is None:
                return FrontendInputResult(state=set_flash(state, "error", "Kein Spielerzustand für Reihenwahl vorhanden."))
            row_mapping = build_row_display_mapping(player_state.public_state.rows)
            if normalized not in row_mapping:
                return FrontendInputResult(state=set_flash(state, "error", "Bitte eine gültige Reihennummer eingeben."))
            next_state = clear_flash(_set_screen(state, GameScreen(kind="waiting", player_state=state.player_state)))
            return FrontendInputResult(state=next_state, action=UiActionChooseRow(row_mapping[normalized]))
        case GameScreen(kind="ended"):
            if normalized != "":
                return FrontendInputResult(state=state)
            return FrontendInputResult(state=apply_frontend_state(state, replace(state.frontend_state, should_exit=True)))
    raise TypeError(f"unsupported screen: {screen!r}")



def _parse_lobby_main(state: CliState, text: str) -> FrontendInputResult:
    if text == "n":
        return FrontendInputResult(state=clear_flash(_set_screen(state, LobbyScreen(kind="rename"))))
    if text == "g":
        return FrontendInputResult(state=clear_flash(state), action=UiActionStartGame())
    if text.isdigit():
        seat_index = int(text)
        if not _is_valid_seat_index(state, seat_index):
            return FrontendInputResult(state=set_flash(state, "error", "Ungültiger Platz."))
        return FrontendInputResult(state=clear_flash(_set_screen(state, LobbyScreen(kind="seat_edit", seat_index=seat_index))))
    return FrontendInputResult(state=set_flash(state, "error", "Ungültige Eingabe. Erlaubt sind n, g oder eine Platznummer."))



def _parse_lobby_seat_edit(state: CliState, text: str, seat_index: int) -> FrontendInputResult:
    if text == "m":
        return FrontendInputResult(
            state=clear_flash(_set_screen(state, LobbyScreen(kind="main"))),
            action=UiActionAssignSelfToSeat(seat_index),
        )
    if text == "b":
        return FrontendInputResult(state=clear_flash(_set_screen(state, LobbyScreen(kind="bot_name", seat_index=seat_index))))
    if text == "c":
        return FrontendInputResult(
            state=clear_flash(_set_screen(state, LobbyScreen(kind="main"))),
            action=UiActionClearSeat(seat_index),
        )
    if text == "x":
        return FrontendInputResult(state=clear_flash(_set_screen(state, LobbyScreen(kind="main"))))
    return FrontendInputResult(state=set_flash(state, "error", "Ungültige Eingabe. Erlaubt sind m, b, c oder x."))



def _parse_lobby_bot_name(state: CliState, text: str, seat_index: int) -> FrontendInputResult:
    if text == "x":
        return FrontendInputResult(state=clear_flash(_set_screen(state, LobbyScreen(kind="seat_edit", seat_index=seat_index))))
    bot_name = text or _default_bot_name(state, seat_index)
    return FrontendInputResult(
        state=clear_flash(_set_screen(state, LobbyScreen(kind="main"))),
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



def _set_screen(state: CliState, screen) -> CliState:
    return apply_frontend_state(state, replace(state.frontend_state, screen=screen))
