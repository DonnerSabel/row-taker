from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from row_taker.cli.row_display import build_row_display_mapping
from row_taker.cli.state_models import (
    CliState,
    GameScreen,
    LobbyScreen,
    UiMessage,
    apply_client_core_state,
    extract_client_core_state,
    has_pending_presentation,
)
from row_taker.client.core_reducer import (
    advance_presentation_queue as advance_core_presentation_queue,
)
from row_taker.client.core_reducer import (
    append_presentation_events as append_core_presentation_events,
)
from row_taker.client.core_reducer import (
    reduce_server_message as reduce_core_server_message,
)
from row_taker.client.core_reducer import (
    reset_presentation_queue as reset_core_presentation_queue,
)
from row_taker.client.core_state import ClientMode, PendingAction
from row_taker.client.presentation_events import PresentationEvent
from row_taker.engine.game.player_state_ops import validate_submit_card, validate_submit_row_choice
from row_taker.protocol.messages import (
    AssignSeatToClient,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    IdentityAssigned,
    LeaveSession,
    LobbyActionRejected,
    RequestStartGame,
    ServerError,
    ServerToClientMessage,
    SessionEnded,
    SetDisplayName,
    SubmitCard,
    SubmitRowChoice,
)

logger = logging.getLogger("row_taker.cli.state_machine")


@dataclass(frozen=True, slots=True)
class UserInputResult:
    state: CliState
    outbound_message: ClientToServerMessage | None = None


def append_presentation_events(state: CliState, events: tuple[PresentationEvent, ...]) -> CliState:
    core = append_core_presentation_events(extract_client_core_state(state), events)
    return apply_client_core_state(state, core)


def reset_presentation_queue(state: CliState) -> CliState:
    core = reset_core_presentation_queue(extract_client_core_state(state))
    return apply_client_core_state(state, core)


def advance_presentation_queue(state: CliState) -> CliState:
    if not state.pending_presentation_events:
        return state
    next_event = state.pending_presentation_events[0]
    logger.debug(
        "presentation advanced: event=%s remaining_before=%s",
        type(next_event).__name__,
        len(state.pending_presentation_events),
    )
    core = advance_core_presentation_queue(extract_client_core_state(state))
    return apply_client_core_state(state, core)


def reduce_server_message(state: CliState, message: ServerToClientMessage) -> CliState:
    core = reduce_core_server_message(extract_client_core_state(state), message)
    state = apply_client_core_state(state, core)

    match message:
        case IdentityAssigned():
            return state
        case LobbyActionRejected(message=text):
            return _with_flash(state, "error", text)
        case SessionEnded(message=text):
            logger.debug("session ended applied: message=%r", text)
            return replace(
                state,
                session_error=text,
                client_mode=ClientMode.ENDED,
                pending_action=PendingAction.NONE,
                exit_on_ack=False,
                suppress_final_result=True,
                should_exit=True,
                flash_message=None,
            )
        case ServerError(message=text):
            return replace(
                state,
                session_error=text,
                exit_on_ack=True,
                suppress_final_result=True,
                flash_message=None,
            )
        case ChooseCardRequested(player_id=player_id, state=player_state):
            return replace(
                state,
                own_player_id=player_id,
                screen=GameScreen(kind="choose_card", player_state=player_state),
                client_mode=ClientMode.GAME,
                pending_action=PendingAction.CHOOSE_CARD,
                flash_message=None,
            )
        case ChooseRowRequested(player_id=player_id, state=player_state):
            return replace(
                state,
                own_player_id=player_id,
                screen=GameScreen(kind="choose_row", player_state=player_state),
                client_mode=ClientMode.GAME,
                pending_action=PendingAction.CHOOSE_ROW,
                flash_message=None,
            )
        case _:
            return _sync_cli_screen_after_server_message(state)


def reduce_user_input(state: CliState, text: str) -> UserInputResult:
    normalized = text.strip()

    if normalized == "X":
        return UserInputResult(
            state=replace(state, should_exit=True, suppress_final_result=True),
            outbound_message=LeaveSession(),
        )

    if state.session_error is not None:
        return _reduce_session_error_input(state, normalized)

    if has_pending_presentation(state):
        if normalized == "":
            return UserInputResult(state=advance_presentation_queue(state))
        return UserInputResult(state=_with_flash(state, "info", "Bitte zuerst die lokale Auflösung mit Enter weiterführen."))

    match state.screen:
        case LobbyScreen(kind="main"):
            return _reduce_lobby_main_input(state, normalized)
        case LobbyScreen(kind="rename"):
            return _reduce_lobby_rename_input(state, normalized)
        case LobbyScreen(kind="seat_edit", seat_index=seat_index):
            if seat_index is None:
                raise TypeError("seat_edit screen requires seat_index")
            return _reduce_lobby_seat_edit_input(state, normalized, seat_index)
        case LobbyScreen(kind="bot_name", seat_index=seat_index):
            if seat_index is None:
                raise TypeError("bot_name screen requires seat_index")
            return _reduce_lobby_bot_name_input(state, normalized, seat_index)
        case GameScreen(kind="waiting"):
            return _reduce_game_waiting_input(state, normalized)
        case GameScreen(kind="choose_card", player_state=player_state):
            if player_state is None:
                raise TypeError("choose_card screen requires player_state")
            return _reduce_game_choose_card_input(state, normalized, player_state)
        case GameScreen(kind="choose_row", player_state=player_state):
            if player_state is None:
                raise TypeError("choose_row screen requires player_state")
            return _reduce_game_choose_row_input(state, normalized, player_state)
        case GameScreen(kind="ended"):
            return _reduce_game_ended_input(state, normalized)

    raise TypeError(f"unsupported screen: {state.screen!r}")


def _sync_cli_screen_after_server_message(state: CliState) -> CliState:
    if state.client_mode == ClientMode.LOBBY:
        current = state.screen
        if isinstance(current, LobbyScreen):
            return state
        return replace(state, screen=LobbyScreen(kind="main"))

    if state.client_mode == ClientMode.ENDED:
        return replace(state, screen=GameScreen(kind="ended"))

    if state.pending_action == PendingAction.CHOOSE_CARD:
        return state
    if state.pending_action == PendingAction.CHOOSE_ROW:
        return state

    current = state.screen
    if isinstance(current, GameScreen) and current.kind == "choose_row":
        return replace(state, screen=GameScreen(kind="waiting"))
    if isinstance(current, GameScreen):
        return state
    return replace(state, screen=GameScreen(kind="waiting"))


def _with_flash(state: CliState, level: str, text: str) -> CliState:
    return replace(state, flash_message=UiMessage(level=level, text=text))


def _reduce_session_error_input(state: CliState, text: str) -> UserInputResult:
    if not state.exit_on_ack:
        return UserInputResult(state=replace(state, should_exit=True))
    if text != "":
        return UserInputResult(state=state)
    return UserInputResult(state=replace(state, should_exit=True))


def _reduce_lobby_main_input(state: CliState, text: str) -> UserInputResult:
    if text == "n":
        return UserInputResult(state=replace(state, screen=LobbyScreen(kind="rename"), flash_message=None))
    if text == "g":
        return UserInputResult(
            state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
            outbound_message=RequestStartGame(),
        )
    if text.isdigit():
        seat_index = int(text)
        if not _is_valid_seat_index(state, seat_index):
            return UserInputResult(state=_with_flash(replace(state, screen=LobbyScreen(kind="main")), "error", "Ungültiger Platz."))
        return UserInputResult(
            state=replace(state, screen=LobbyScreen(kind="seat_edit", seat_index=seat_index), flash_message=None)
        )
    return UserInputResult(
        state=_with_flash(
            replace(state, screen=LobbyScreen(kind="main")),
            "error",
            "Ungültige Eingabe. Erlaubt sind n, g oder eine Platznummer.",
        )
    )


def _reduce_lobby_rename_input(state: CliState, text: str) -> UserInputResult:
    if text == "":
        return UserInputResult(
            state=_with_flash(
                replace(state, screen=LobbyScreen(kind="rename")),
                "error",
                "Der Anzeigename darf nicht leer sein.",
            )
        )
    return UserInputResult(
        state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
        outbound_message=SetDisplayName(display_name=text),
    )


def _reduce_lobby_seat_edit_input(state: CliState, text: str, seat_index: int) -> UserInputResult:
    if text == "m":
        if state.own_client_id is None:
            return UserInputResult(state=_with_flash(state, "error", "Eigene client_id unbekannt."))
        return UserInputResult(
            state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
            outbound_message=AssignSeatToClient(seat_index=seat_index, target_client_id=state.own_client_id),
        )
    if text == "b":
        return UserInputResult(
            state=replace(state, screen=LobbyScreen(kind="bot_name", seat_index=seat_index), flash_message=None)
        )
    if text == "c":
        return UserInputResult(
            state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
            outbound_message=ClearSeat(seat_index=seat_index),
        )
    if text == "x":
        return UserInputResult(state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None))
    return UserInputResult(
        state=_with_flash(
            replace(state, screen=LobbyScreen(kind="seat_edit", seat_index=seat_index)),
            "error",
            "Ungültige Eingabe. Erlaubt sind m, b, c oder x.",
        )
    )


def _reduce_lobby_bot_name_input(state: CliState, text: str, seat_index: int) -> UserInputResult:
    if text == "x":
        return UserInputResult(
            state=replace(state, screen=LobbyScreen(kind="seat_edit", seat_index=seat_index), flash_message=None)
        )
    bot_name = text or _default_bot_name(state, seat_index)
    return UserInputResult(
        state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
        outbound_message=CreateLocalBotOnSeat(seat_index=seat_index, display_name=bot_name),
    )


def _reduce_game_waiting_input(state: CliState, text: str) -> UserInputResult:
    if text == "":
        return UserInputResult(state=state)
    return UserInputResult(state=_with_flash(state, "info", "Bitte auf den nächsten Spielschritt warten."))


def _reduce_game_choose_card_input(state: CliState, text: str, player_state) -> UserInputResult:
    if text == "":
        return UserInputResult(state=_with_flash(state, "error", "Bitte einen Kartenwert eingeben."))
    try:
        card_value = int(text)
    except ValueError:
        return UserInputResult(state=_with_flash(state, "error", "Bitte einen gültigen Kartenwert eingeben."))
    try:
        validate_submit_card(player_state, card_value)
    except ValueError as exc:
        return UserInputResult(state=_with_flash(state, "error", str(exc)))
    return UserInputResult(
        state=replace(state, screen=GameScreen(kind="waiting"), pending_action=PendingAction.NONE, flash_message=None),
        outbound_message=SubmitCard(card_value=card_value),
    )


def _reduce_game_choose_row_input(state: CliState, text: str, player_state) -> UserInputResult:
    row_mapping = build_row_display_mapping(player_state.public_state.rows)
    if text not in row_mapping:
        return UserInputResult(state=_with_flash(state, "error", "Bitte eine gültige Reihennummer eingeben."))
    row_id = row_mapping[text]
    try:
        validate_submit_row_choice(player_state, row_id)
    except ValueError as exc:
        return UserInputResult(state=_with_flash(state, "error", str(exc)))
    return UserInputResult(
        state=replace(state, screen=GameScreen(kind="waiting"), pending_action=PendingAction.NONE, flash_message=None),
        outbound_message=SubmitRowChoice(row_id=row_id),
    )


def _reduce_game_ended_input(state: CliState, text: str) -> UserInputResult:
    if text != "":
        return UserInputResult(state=state)
    return UserInputResult(state=replace(state, should_exit=True))


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
