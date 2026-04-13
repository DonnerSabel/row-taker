from __future__ import annotations

from dataclasses import dataclass, replace

from row_taker.cli.local_resolution import apply_local_row_choice, start_local_resolution
from row_taker.cli.row_display import build_row_display_mapping
from row_taker.cli.state_models import CliState, GameScreen, LobbyScreen, UiMessage
from row_taker.engine.game.player_state_ops import validate_submit_card, validate_submit_row_choice
from row_taker.protocol.messages import (
    AssignSeatToClient,
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameStarting,
    IdentityAssigned,
    LeaveSession,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    RowChoiceCommitted,
    ServerError,
    ServerToClientMessage,
    SessionEnded,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
)


@dataclass(frozen=True, slots=True)
class UserInputResult:
    state: CliState
    outbound_message: ClientToServerMessage | None = None


def reduce_server_message(state: CliState, message: ServerToClientMessage) -> CliState:
    match message:
        case IdentityAssigned(client_id=client_id):
            return replace(state, own_client_id=client_id)
        case LobbyStateUpdated(lobby=lobby):
            return replace(state, lobby_view=lobby)
        case LobbyActionRejected(message=text):
            return _with_flash(state, "error", text)
        case GameStarting(lobby=lobby):
            return replace(
                state,
                lobby_view=lobby,
                public_state=None,
                screen=GameScreen(kind="waiting"),
                flash_message=UiMessage(level="info", text="Spielstart..."),
                revealed_trick=None,
                local_resolution=None,
                resolution_lines=(),
            )
        case StateUpdated(state=public_state):
            next_screen = state.screen
            if isinstance(next_screen, GameScreen) and next_screen.kind == "choose_row":
                next_screen = GameScreen(kind="waiting")
            next_local_resolution = state.local_resolution
            if next_local_resolution is not None and next_local_resolution.pending_row_choice is None:
                next_local_resolution = None
            return replace(state, public_state=public_state, screen=next_screen, revealed_trick=None, local_resolution=next_local_resolution)
        case CardsRevealed() as revealed:
            local_resolution = None
            resolution_lines = ()
            if state.public_state is not None:
                local_resolution = start_local_resolution(state.public_state, revealed)
                resolution_lines = local_resolution.lines
            return replace(state, revealed_trick=revealed, local_resolution=local_resolution, resolution_lines=resolution_lines, flash_message=None)
        case RowChoiceCommitted(row_id=row_id):
            local_resolution = state.local_resolution
            resolution_lines = state.resolution_lines
            if local_resolution is not None and local_resolution.pending_row_choice is not None:
                local_resolution = apply_local_row_choice(local_resolution, row_id)
                resolution_lines = local_resolution.lines
            return replace(state, screen=GameScreen(kind="waiting"), local_resolution=local_resolution, resolution_lines=resolution_lines, flash_message=None)
        case ChooseCardRequested(player_id=player_id, state=player_state):
            return replace(
                state,
                own_player_id=player_id,
                screen=GameScreen(kind="choose_card", player_state=player_state),
                flash_message=None,
                revealed_trick=None,
                local_resolution=None,
                resolution_lines=(),
            )
        case ChooseRowRequested(player_id=player_id, state=player_state):
            return replace(
                state,
                own_player_id=player_id,
                screen=GameScreen(kind="choose_row", player_state=player_state),
                flash_message=None,
            )
        case SessionEnded(message=text):
            return replace(
                state,
                session_error=text,
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
        case _:
            raise TypeError(f"unsupported server message type: {type(message)!r}")


def reduce_user_input(state: CliState, text: str) -> UserInputResult:
    normalized = text.strip()

    if normalized == "X":
        return UserInputResult(
            state=replace(state, should_exit=True, suppress_final_result=True),
            outbound_message=LeaveSession(),
        )

    if state.session_error is not None:
        return _reduce_session_error_input(state, normalized)

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
    seat_screen = LobbyScreen(kind="seat_edit", seat_index=seat_index)
    if text == "m":
        if state.own_client_id is None:
            return UserInputResult(
                state=_with_flash(
                    replace(state, screen=seat_screen),
                    "error",
                    "Eigene client_id noch nicht zugewiesen. Bitte kurz warten.",
                )
            )
        return UserInputResult(
            state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
            outbound_message=AssignSeatToClient(
                seat_index=seat_index,
                target_client_id=state.own_client_id,
            ),
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
            replace(state, screen=seat_screen),
            "error",
            "Ungültige Eingabe. Erlaubt sind m, b, c oder x.",
        )
    )


def _current_bot_name(state: CliState, seat_index: int) -> str:
    lobby = state.lobby_view
    if lobby is not None:
        for seat in lobby.seats:
            if seat.seat_index == seat_index and seat.occupant_kind == "bot" and seat.occupant_display_name:
                return seat.occupant_display_name
    return f"Bot_{seat_index}"


def _reduce_lobby_bot_name_input(state: CliState, text: str, seat_index: int) -> UserInputResult:
    if text == "x":
        return UserInputResult(state=replace(state, screen=LobbyScreen(kind="seat_edit", seat_index=seat_index), flash_message=None))
    display_name = text or _current_bot_name(state, seat_index)
    return UserInputResult(
        state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
        outbound_message=CreateLocalBotOnSeat(seat_index=seat_index, display_name=display_name),
    )


def _reduce_game_waiting_input(state: CliState, text: str) -> UserInputResult:
    if text == "":
        return UserInputResult(state=state)
    return UserInputResult(state=_with_flash(state, "info", "Momentan ist keine Eingabe erforderlich."))


def _reduce_game_choose_card_input(state: CliState, text: str, player_state) -> UserInputResult:
    if not text.isdigit():
        return UserInputResult(
            state=_with_flash(state, "error", "Bitte gib die Zahl einer Handkarte ein.")
        )
    card_value = int(text)
    try:
        validate_submit_card(player_state, card_value)
    except ValueError:
        return UserInputResult(
            state=_with_flash(state, "error", "Diese Karte befindet sich nicht auf deiner Hand.")
        )
    return UserInputResult(
        state=replace(state, screen=GameScreen(kind="waiting"), flash_message=None),
        outbound_message=SubmitCard(card_value=card_value),
    )


def _reduce_game_choose_row_input(state: CliState, text: str, player_state) -> UserInputResult:
    mapping = build_row_display_mapping(player_state.public_state)
    if not text.isdigit():
        return UserInputResult(
            state=_with_flash(
                state,
                "error",
                f"Bitte gib eine Zahl zwischen 1 und {mapping.max_cli_row()} ein.",
            )
        )
    cli_row = int(text)
    if not (1 <= cli_row <= mapping.max_cli_row()):
        return UserInputResult(
            state=_with_flash(
                state,
                "error",
                f"Ungültige Reihe. Erlaubt sind 1 bis {mapping.max_cli_row()}.",
            )
        )
    state_row_index = mapping.to_state_index(cli_row)
    row_id = player_state.rows[state_row_index].row_id
    try:
        validate_submit_row_choice(player_state, row_id)
    except ValueError:
        return UserInputResult(
            state=_with_flash(state, "error", "Diese Reihe ist momentan nicht wählbar.")
        )
    return UserInputResult(
        state=replace(state, screen=GameScreen(kind="waiting"), flash_message=None),
        outbound_message=SubmitRowChoice(row_id=row_id),
    )


def _reduce_game_ended_input(state: CliState, text: str) -> UserInputResult:
    if text != "":
        return UserInputResult(state=state)
    return UserInputResult(state=replace(state, should_exit=True))


def _is_valid_seat_index(state: CliState, seat_index: int) -> bool:
    if state.lobby_view is None:
        return False
    return 0 <= seat_index < state.lobby_view.seat_count
