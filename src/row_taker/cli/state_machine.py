from __future__ import annotations

from dataclasses import dataclass, replace

from row_taker.cli.row_display import build_row_display_mapping
from row_taker.cli.state_models import (
    CliState,
    GameStateChooseCard,
    GameStateChooseRow,
    GameStateEnded,
    GameStateTrickResolved,
    GameStateWaiting,
    LobbyStateMain,
    LobbyStateRename,
    LobbyStateSeatEdit,
)
from row_taker.engine.game.player_state_ops import validate_submit_card, validate_submit_row_choice
from row_taker.protocol.messages import (
    AssignSeatToClient,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameStarting,
    IdentityAssigned,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    ServerError,
    ServerToClientMessage,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
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
            return replace(state, mode=_apply_lobby_error(state.mode, text))

        case GameStarting(lobby=lobby):
            return replace(
                state,
                lobby_view=lobby,
                public_state=None,
                mode=GameStateWaiting(info_message="Spielstart..."),
                pending_next_state=None,
            )

        case StateUpdated(state=public_state):
            return replace(state, public_state=public_state)

        case ChooseCardRequested(player_id=player_id, state=player_state):
            next_mode = GameStateChooseCard(player_state=player_state)
            state = replace(state, own_player_id=player_id)
            if isinstance(state.mode, GameStateTrickResolved):
                return replace(state, pending_next_state=next_mode)
            return replace(state, mode=next_mode)

        case ChooseRowRequested(player_id=player_id, state=player_state):
            next_mode = GameStateChooseRow(player_state=player_state)
            state = replace(state, own_player_id=player_id)
            if isinstance(state.mode, GameStateTrickResolved):
                return replace(state, pending_next_state=next_mode)
            return replace(state, mode=next_mode)

        case TrickResolved() as resolved:
            return replace(
                state,
                mode=GameStateTrickResolved(
                    public_state_before=state.public_state,
                    resolved=resolved,
                ),
                pending_next_state=None,
            )

        case ServerError(message=text):
            return replace(state, session_error=text, should_exit=True)

        case _:
            raise TypeError(f"unsupported server message type: {type(message)!r}")


def reduce_user_input(state: CliState, text: str) -> UserInputResult:
    normalized = text.strip()

    match state.mode:
        case LobbyStateMain():
            return _reduce_lobby_main_input(state, normalized)
        case LobbyStateRename():
            return _reduce_lobby_rename_input(state, normalized)
        case LobbyStateSeatEdit(seat_index=seat_index):
            return _reduce_lobby_seat_edit_input(state, normalized, seat_index)
        case GameStateWaiting():
            return _reduce_game_waiting_input(state, normalized)
        case GameStateChooseCard(player_state=player_state):
            return _reduce_game_choose_card_input(state, normalized, player_state)
        case GameStateChooseRow(player_state=player_state):
            return _reduce_game_choose_row_input(state, normalized, player_state)
        case GameStateTrickResolved():
            return _reduce_game_trick_resolved_input(state, normalized)
        case GameStateEnded():
            return _reduce_game_ended_input(state, normalized)

    raise TypeError(f"unsupported mode: {type(state.mode)!r}")


def _apply_lobby_error(mode: object, text: str) -> object:
    match mode:
        case LobbyStateMain():
            return LobbyStateMain(error_message=text)
        case LobbyStateRename():
            return LobbyStateRename(error_message=text)
        case LobbyStateSeatEdit(seat_index=seat_index):
            return LobbyStateSeatEdit(seat_index=seat_index, error_message=text)
        case _:
            return mode


def _reduce_lobby_main_input(state: CliState, text: str) -> UserInputResult:
    if text == "n":
        return UserInputResult(state=replace(state, mode=LobbyStateRename()))

    if text == "g":
        return UserInputResult(
            state=replace(state, mode=LobbyStateMain()),
            outbound_message=RequestStartGame(),
        )

    if text.isdigit():
        seat_index = int(text)
        if not _is_valid_seat_index(state, seat_index):
            return UserInputResult(
                state=replace(state, mode=LobbyStateMain(error_message="Ungültiger Platz."))
            )
        return UserInputResult(
            state=replace(state, mode=LobbyStateSeatEdit(seat_index=seat_index))
        )

    return UserInputResult(
        state=replace(
            state,
            mode=LobbyStateMain(
                error_message="Ungültige Eingabe. Erlaubt sind n, g oder eine Platznummer."
            ),
        )
    )


def _reduce_lobby_rename_input(state: CliState, text: str) -> UserInputResult:
    if text == "":
        return UserInputResult(
            state=replace(
                state,
                mode=LobbyStateRename(
                    error_message="Der Anzeigename darf nicht leer sein."
                ),
            )
        )

    return UserInputResult(
        state=replace(state, mode=LobbyStateMain()),
        outbound_message=SetDisplayName(display_name=text),
    )


def _reduce_lobby_seat_edit_input(
    state: CliState,
    text: str,
    seat_index: int,
) -> UserInputResult:
    if text == "m":
        if state.own_client_id is None:
            return UserInputResult(
                state=replace(
                    state,
                    mode=LobbyStateSeatEdit(
                        seat_index=seat_index,
                        error_message="Eigene client_id noch nicht zugewiesen. Bitte kurz warten.",
                    ),
                )
            )
        return UserInputResult(
            state=replace(state, mode=LobbyStateMain()),
            outbound_message=AssignSeatToClient(
                seat_index=seat_index,
                target_client_id=state.own_client_id,
            ),
        )

    if text == "b":
        return UserInputResult(
            state=replace(state, mode=LobbyStateMain()),
            outbound_message=CreateLocalBotOnSeat(
                seat_index=seat_index,
                display_name=f"Bot_{seat_index}",
            ),
        )

    if text == "c":
        return UserInputResult(
            state=replace(state, mode=LobbyStateMain()),
            outbound_message=ClearSeat(seat_index=seat_index),
        )

    if text == "x":
        return UserInputResult(state=replace(state, mode=LobbyStateMain()))

    return UserInputResult(
        state=replace(
            state,
            mode=LobbyStateSeatEdit(
                seat_index=seat_index,
                error_message="Ungültige Eingabe. Erlaubt sind m, b, c oder x.",
            ),
        )
    )


def _reduce_game_waiting_input(state: CliState, text: str) -> UserInputResult:
    if text == "":
        return UserInputResult(state=state)
    return UserInputResult(
        state=replace(
            state,
            mode=GameStateWaiting(info_message="Momentan ist keine Eingabe erforderlich."),
        )
    )


def _reduce_game_choose_card_input(
    state: CliState,
    text: str,
    player_state,
) -> UserInputResult:
    if not text.isdigit():
        return UserInputResult(
            state=replace(
                state,
                mode=GameStateChooseCard(
                    player_state=player_state,
                    error_message="Bitte gib die Zahl einer Handkarte ein.",
                ),
            )
        )

    card_value = int(text)
    try:
        validate_submit_card(player_state, card_value)
    except ValueError:
        return UserInputResult(
            state=replace(
                state,
                mode=GameStateChooseCard(
                    player_state=player_state,
                    error_message="Diese Karte befindet sich nicht auf deiner Hand.",
                ),
            )
        )

    return UserInputResult(
        state=replace(state, mode=GameStateWaiting()),
        outbound_message=SubmitCard(
            player_id=player_state.self_player_id,
            card_value=card_value,
        ),
    )


def _reduce_game_choose_row_input(
    state: CliState,
    text: str,
    player_state,
) -> UserInputResult:
    mapping = build_row_display_mapping(player_state.public_state)

    if not text.isdigit():
        return UserInputResult(
            state=replace(
                state,
                mode=GameStateChooseRow(
                    player_state=player_state,
                    error_message=f"Bitte gib eine Zahl zwischen 1 und {mapping.max_cli_row()} ein.",
                ),
            )
        )

    cli_row = int(text)
    if not (1 <= cli_row <= mapping.max_cli_row()):
        return UserInputResult(
            state=replace(
                state,
                mode=GameStateChooseRow(
                    player_state=player_state,
                    error_message=f"Ungültige Reihe. Erlaubt sind 1 bis {mapping.max_cli_row()}.",
                ),
            )
        )

    state_row_index = mapping.to_state_index(cli_row)
    row_id = player_state.rows[state_row_index].row_id
    try:
        validate_submit_row_choice(player_state, row_id)
    except ValueError:
        return UserInputResult(
            state=replace(
                state,
                mode=GameStateChooseRow(
                    player_state=player_state,
                    error_message="Diese Reihe ist momentan nicht wählbar.",
                ),
            )
        )

    return UserInputResult(
        state=replace(state, mode=GameStateWaiting()),
        outbound_message=SubmitRowChoice(
            player_id=player_state.self_player_id,
            row_id=row_id,
        ),
    )


def _reduce_game_trick_resolved_input(state: CliState, text: str) -> UserInputResult:
    mode = state.mode
    if not isinstance(mode, GameStateTrickResolved):
        raise TypeError("expected GameStateTrickResolved")

    if text != "":
        return UserInputResult(
            state=replace(
                state,
                mode=GameStateTrickResolved(
                    public_state_before=mode.public_state_before,
                    resolved=mode.resolved,
                    info_message="Bitte mit Enter fortfahren.",
                ),
            )
        )

    next_mode = state.pending_next_state
    if next_mode is None:
        if mode.resolved.game_finished:
            next_mode = GameStateEnded()
        else:
            next_mode = GameStateWaiting()

    return UserInputResult(
        state=replace(state, mode=next_mode, pending_next_state=None)
    )


def _reduce_game_ended_input(state: CliState, text: str) -> UserInputResult:
    if text != "":
        return UserInputResult(state=state)
    return UserInputResult(state=replace(state, should_exit=True))


def _is_valid_seat_index(state: CliState, seat_index: int) -> bool:
    if state.lobby_view is None:
        return False
    return 0 <= seat_index < state.lobby_view.seat_count

