from __future__ import annotations

from dataclasses import dataclass

from row_taker.cli.row_display import build_row_display_mapping
from row_taker.cli.state_models import (
    CliState,
    GameScreen,
    LobbyScreen,
    UiMessage,
    has_pending_presentation,
    with_feedback_updates,
    with_screen,
)
from row_taker.client.actions import (
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


@dataclass(frozen=True, slots=True)
class FrontendInputResult:
    state: CliState
    action: object | None = None


class CliFrontend:
    def sync_to_core(self, state: CliState) -> CliState:
        return state

    def handle_text_input(self, state: CliState, text: str) -> FrontendInputResult:
        return parse_text_to_action(state, text)

    def clear_flash(self, state: CliState) -> CliState:
        return clear_flash(state)


def set_flash(state: CliState, level: str, text: str) -> CliState:
    return with_feedback_updates(state, flash_message=UiMessage(level=level, text=text))


def clear_flash(state: CliState) -> CliState:
    return with_feedback_updates(state, flash_message=None)


def parse_text_to_action(state: CliState, text: str) -> FrontendInputResult:
    normalized = text.strip()

    if normalized == "X":
        return FrontendInputResult(
            state=with_feedback_updates(state, should_exit=True, suppress_final_result=True),
            action=UiActionLeaveSession(),
        )

    if state.session_error is not None:
        if not state.exit_on_ack:
            return FrontendInputResult(state=with_feedback_updates(state, should_exit=True))
        if normalized == "":
            return FrontendInputResult(state=with_feedback_updates(state, should_exit=True))
        return FrontendInputResult(state=state)

    if has_pending_presentation(state):
        if normalized == "":
            return FrontendInputResult(state=state, action=UiActionAdvancePresentation())
        return FrontendInputResult(state=set_flash(state, "info", "Bitte zuerst die lokale Auflösung mit Enter weiterführen."))

    match state.screen:
        case LobbyScreen(kind="main"):
            return _parse_lobby_main(state, normalized)
        case LobbyScreen(kind="rename"):
            return _parse_lobby_rename(state, normalized)
        case LobbyScreen(kind="seat_edit", seat_index=seat_index):
            return _parse_lobby_seat_edit(state, normalized, seat_index)
        case LobbyScreen(kind="bot_name", seat_index=seat_index):
            return _parse_lobby_bot_name(state, normalized, seat_index)
        case GameScreen(kind="waiting"):
            return FrontendInputResult(state=state)
        case GameScreen(kind="choose_card"):
            return _parse_game_choose_card(state, normalized)
        case GameScreen(kind="choose_row"):
            return _parse_game_choose_row(state, normalized)
        case GameScreen(kind="ended"):
            if normalized == "":
                return FrontendInputResult(state=with_feedback_updates(state, should_exit=True))
            return FrontendInputResult(state=state)
    raise TypeError(f"unsupported screen: {state.screen!r}")


def _parse_lobby_main(state: CliState, text: str) -> FrontendInputResult:
    if text == "n":
        next_state = with_screen(state, LobbyScreen(kind="rename"))
        next_state = with_feedback_updates(next_state, flash_message=None)
        return FrontendInputResult(state=next_state)
    if text == "g":
        return FrontendInputResult(state=clear_flash(state), action=UiActionStartGame())
    if text.isdigit():
        seat_index = int(text)
        if state.lobby_view is None or not (0 <= seat_index < state.lobby_view.seat_count):
            return FrontendInputResult(state=set_flash(with_screen(state, LobbyScreen(kind="main")), "error", "Ungültiger Platz."))
        next_state = with_screen(state, LobbyScreen(kind="seat_edit", seat_index=seat_index))
        next_state = with_feedback_updates(next_state, flash_message=None)
        return FrontendInputResult(state=next_state)
    return FrontendInputResult(state=set_flash(with_screen(state, LobbyScreen(kind="main")), "error", "Ungültige Eingabe. Erlaubt sind n, g oder eine Platznummer."))


def _parse_lobby_rename(state: CliState, text: str) -> FrontendInputResult:
    if text == "":
        return FrontendInputResult(state=set_flash(with_screen(state, LobbyScreen(kind="rename")), "error", "Der Anzeigename darf nicht leer sein."))
    next_state = with_screen(state, LobbyScreen(kind="main"))
    next_state = with_feedback_updates(next_state, flash_message=None)
    return FrontendInputResult(state=next_state, action=UiActionRename(text))


def _parse_lobby_seat_edit(state: CliState, text: str, seat_index: int | None) -> FrontendInputResult:
    if seat_index is None:
        raise TypeError("seat_edit screen requires seat_index")
    if text == "m":
        return FrontendInputResult(state=clear_flash(state), action=UiActionAssignSelfToSeat(seat_index))
    if text == "b":
        next_state = with_screen(state, LobbyScreen(kind="bot_name", seat_index=seat_index))
        next_state = with_feedback_updates(next_state, flash_message=None)
        return FrontendInputResult(state=next_state)
    if text == "c":
        return FrontendInputResult(state=clear_flash(state), action=UiActionClearSeat(seat_index))
    if text == "x":
        next_state = with_screen(state, LobbyScreen(kind="main"))
        next_state = with_feedback_updates(next_state, flash_message=None)
        return FrontendInputResult(state=next_state)
    return FrontendInputResult(state=set_flash(with_screen(state, LobbyScreen(kind="seat_edit", seat_index=seat_index)), "error", "Ungültige Eingabe. Erlaubt sind m, b, c oder x."))


def _parse_lobby_bot_name(state: CliState, text: str, seat_index: int | None) -> FrontendInputResult:
    if seat_index is None:
        raise TypeError("bot_name screen requires seat_index")
    if text == "x":
        next_state = with_screen(state, LobbyScreen(kind="seat_edit", seat_index=seat_index))
        next_state = with_feedback_updates(next_state, flash_message=None)
        return FrontendInputResult(state=next_state)
    display_name = text or f"Bot_{seat_index}"
    next_state = with_screen(state, LobbyScreen(kind="main"))
    next_state = with_feedback_updates(next_state, flash_message=None)
    return FrontendInputResult(state=next_state, action=UiActionCreateBot(seat_index, display_name))


def _parse_game_choose_card(state: CliState, text: str) -> FrontendInputResult:
    try:
        value = int(text)
    except ValueError:
        return FrontendInputResult(state=set_flash(state, "error", "Bitte eine Kartenzahl eingeben."))
    return FrontendInputResult(state=clear_flash(state), action=UiActionChooseCard(value))


def _parse_game_choose_row(state: CliState, text: str) -> FrontendInputResult:
    screen = state.screen
    if not isinstance(screen, GameScreen) or screen.player_state is None:
        raise TypeError("expected choose_row screen with player_state")
    try:
        cli_row = int(text)
    except ValueError:
        return FrontendInputResult(state=set_flash(state, "error", "Bitte eine Reihennummer eingeben."))
    mapping = build_row_display_mapping(screen.player_state.public_state)
    if cli_row < 1 or cli_row > mapping.max_cli_row():
        return FrontendInputResult(state=set_flash(state, "error", "Ungültige Reihennummer."))
    row_id = screen.player_state.public_state.rows[mapping.to_state_index(cli_row)].row_id
    return FrontendInputResult(state=clear_flash(state), action=UiActionChooseRow(row_id))
