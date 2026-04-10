from __future__ import annotations

from row_taker.cli.row_display import build_row_display_mapping, format_public_deltas_for_cli
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
from row_taker.engine.game.public_state_ops import apply_deltas_public_state
from row_taker.engine.game.state import PlayerState, PublicState
from row_taker.protocol.messages import LobbySeatView, TrickResolved


def get_prompt(state: CliState) -> str | None:
    match state.mode:
        case LobbyStateMain():
            return "Auswahl > "
        case LobbyStateRename():
            return "Neuer Anzeigename > "
        case LobbyStateSeatEdit(seat_index=seat_index):
            return f"Platz {seat_index} > "
        case GameStateWaiting():
            return None
        case GameStateChooseCard():
            return "Karte > "
        case GameStateChooseRow():
            return "Reihe > "
        case GameStateTrickResolved():
            return "Weiter mit Enter > "
        case GameStateEnded():
            return "Weiter mit Enter > "
        case _:
            raise TypeError(f"unsupported mode: {type(state.mode)!r}")


def render_screen(state: CliState) -> str:
    parts: list[str] = []
    if state.session_error is not None:
        parts.append(render_session_error(state.session_error))

    match state.mode:
        case LobbyStateMain():
            parts.append(render_lobby_main(state))
        case LobbyStateRename():
            parts.append(render_lobby_rename(state))
        case LobbyStateSeatEdit():
            parts.append(render_lobby_seat_edit(state))
        case GameStateWaiting():
            parts.append(render_game_waiting(state))
        case GameStateChooseCard():
            parts.append(render_game_choose_card(state))
        case GameStateChooseRow():
            parts.append(render_game_choose_row(state))
        case GameStateTrickResolved():
            parts.append(render_game_trick_resolved(state))
        case GameStateEnded():
            parts.append(render_game_ended(state))
        case _:
            raise TypeError(f"unsupported mode: {type(state.mode)!r}")

    return "\n\n".join(part for part in parts if part)


def render_session_error(message: str) -> str:
    return "\n".join(["SERVERFEHLER", "-----------", message])


def render_lobby_main(state: CliState) -> str:
    lines = [
        render_lobby_overview(state),
        "",
        "Menü:",
        "  n = Name ändern",
        "  0,1,2,3... = Platz editieren",
        "  g = Spiel starten",
    ]
    mode = state.mode
    if isinstance(mode, LobbyStateMain) and mode.error_message is not None:
        lines.extend(["", f"Fehler: {mode.error_message}"])
    return "\n".join(lines)


def render_lobby_rename(state: CliState) -> str:
    lines = [
        render_lobby_overview(state),
        "",
        "Name ändern",
        "-----------",
        "Bitte neuen Anzeigenamen eingeben.",
    ]
    mode = state.mode
    if isinstance(mode, LobbyStateRename) and mode.error_message is not None:
        lines.extend(["", f"Fehler: {mode.error_message}"])
    return "\n".join(lines)


def render_lobby_seat_edit(state: CliState) -> str:
    mode = state.mode
    if not isinstance(mode, LobbyStateSeatEdit):
        raise TypeError("expected LobbyStateSeatEdit")
    lines = [
        render_lobby_overview_with_highlight(state, mode.seat_index),
        "",
        f"Platz {mode.seat_index} bearbeiten",
        "-------------------------",
        "  m = mich setzen",
        "  b = Bot setzen",
        "  c = Platz leeren",
        "  x = zurück",
    ]
    if mode.error_message is not None:
        lines.extend(["", f"Fehler: {mode.error_message}"])
    return "\n".join(lines)


def render_lobby_overview(state: CliState) -> str:
    lobby = state.lobby_view
    if lobby is None:
        return "\n".join(["Lobby", "-----", "Noch keine Lobby-Daten vorhanden."])

    lines = ["Lobby", "-----", "", "Plätze:"]
    for seat in lobby.seats:
        lines.append(render_lobby_seat_line(state, seat.seat_index, seat))

    lines.extend(["", "Teilnehmer:"])
    participants = sorted(
        lobby.participants,
        key=lambda participant: (
            participant.seat_index is None,
            participant.seat_index if participant.seat_index is not None else 9999,
            participant.display_name.lower(),
        ),
    )
    for participant in participants:
        position = (
            f"Platz {participant.seat_index}"
            if participant.seat_index is not None
            else "nicht gesetzt"
        )
        marker = " <- du" if participant.client_id == state.own_client_id else ""
        lines.append(f"  {participant.display_name} ({participant.participant_kind}, {position}){marker}")
    return "\n".join(lines)


def render_lobby_overview_with_highlight(state: CliState, selected_seat_index: int) -> str:
    lobby = state.lobby_view
    if lobby is None:
        return render_lobby_overview(state)

    lines = ["Lobby", "-----", "", "Plätze:"]
    for seat in lobby.seats:
        prefix = ">" if seat.seat_index == selected_seat_index else " "
        lines.append(f"{prefix} [{seat.seat_index}] {_describe_lobby_seat(state, seat)}")

    lines.extend(["", "Teilnehmer:"])
    participants = sorted(
        lobby.participants,
        key=lambda participant: (
            participant.seat_index is None,
            participant.seat_index if participant.seat_index is not None else 9999,
            participant.display_name.lower(),
        ),
    )
    for participant in participants:
        position = (
            f"Platz {participant.seat_index}"
            if participant.seat_index is not None
            else "nicht gesetzt"
        )
        marker = " <- du" if participant.client_id == state.own_client_id else ""
        lines.append(f"  {participant.display_name} ({participant.participant_kind}, {position}){marker}")
    return "\n".join(lines)


def render_lobby_seat_line(state: CliState, seat_index: int, seat: LobbySeatView) -> str:
    return f"  [{seat_index}] {_describe_lobby_seat(state, seat)}"


def _describe_lobby_seat(state: CliState, seat: LobbySeatView) -> str:
    if seat.occupant_display_name is None:
        return "(leer)"
    label = f"{seat.occupant_display_name} ({seat.occupant_kind})"
    if seat.occupant_client_id == state.own_client_id:
        label += " <- du"
    return label


def render_game_waiting(state: CliState) -> str:
    lines = [render_game_overview(state), "", "Warten auf andere Spieler..."]
    mode = state.mode
    if isinstance(mode, GameStateWaiting) and mode.info_message is not None:
        lines.extend(["", mode.info_message])
    return "\n".join(lines)


def render_game_choose_card(state: CliState) -> str:
    mode = state.mode
    if not isinstance(mode, GameStateChooseCard):
        raise TypeError("expected GameStateChooseCard")
    lines = [
        render_game_overview(state),
        "",
        render_own_hand(mode.player_state),
        "",
        "Du bist dran.",
        "Wähle eine Karte aus deiner Hand.",
    ]
    if mode.error_message is not None:
        lines.extend(["", f"Fehler: {mode.error_message}"])
    return "\n".join(lines)


def render_game_choose_row(state: CliState) -> str:
    mode = state.mode
    if not isinstance(mode, GameStateChooseRow):
        raise TypeError("expected GameStateChooseRow")
    mapping = build_row_display_mapping(mode.player_state.public_state)
    pending_card_value = mode.player_state.pending_card_value()
    pending_card_text = "?" if pending_card_value is None else str(pending_card_value)
    lines = [
        render_game_overview(state),
        "",
        render_own_hand(mode.player_state),
        "",
        f"Deine Karte {pending_card_text} ist kleiner als alle Reihen.",
        f"Bitte wähle eine Reihe zwischen 1 und {mapping.max_cli_row()}.",
    ]
    if mode.error_message is not None:
        lines.extend(["", f"Fehler: {mode.error_message}"])
    return "\n".join(lines)


def render_game_trick_resolved(state: CliState) -> str:
    mode = state.mode
    if not isinstance(mode, GameStateTrickResolved):
        raise TypeError("expected GameStateTrickResolved")
    lines = [
        "Stich aufgelöst",
        "---------------",
        "",
        render_trick_resolved_summary(mode.public_state_before, mode.resolved),
    ]
    if state.public_state is not None:
        lines.extend(["", "Aktueller Stand:", "----------------", "", render_game_overview(state)])
    if mode.info_message is not None:
        lines.extend(["", mode.info_message])
    return "\n".join(lines)


def render_game_ended(state: CliState) -> str:
    lines = ["Spiel beendet", "-------------"]
    if state.public_state is not None:
        lines.extend(["", render_game_overview(state)])
    mode = state.mode
    if isinstance(mode, GameStateEnded) and mode.info_message is not None:
        lines.extend(["", mode.info_message])
    return "\n".join(lines)


def render_game_overview(state: CliState) -> str:
    public_state = state.public_state
    if public_state is None:
        return "\n".join(["Spiel", "-----", "Noch kein öffentlicher Spielzustand vorhanden."])

    lines = [f"Runde: {public_state.round_no}", f"Stich: {public_state.trick_no}", "", "Reihen:"]
    mapping = build_row_display_mapping(public_state)
    for cli_row, state_row_index in enumerate(mapping.row_order, start=1):
        row = public_state.rows[state_row_index]
        vals = " ".join(f"{card.value:>3}" for card in row.cards)
        lines.append(f"  Reihe {cli_row}: {vals:<25} ({row.bullheads()} Hornochsen)")

    lines.extend(["", "Scores:"])
    for index, player in enumerate(public_state.players):
        marker = " <- du" if player.player_id == state.own_player_id else ""
        lines.append(f"  ({index}) {player.name}: {player.score}, {player.hand_count} Karten{marker}")
    return "\n".join(lines)


def render_own_hand(player_state: PlayerState) -> str:
    cards = " ".join(f"|{card.value} {card.bullheads * '🐮'}|" for card in player_state.hand)
    return "\n".join(
        [
            f"{player_state.self_player_name()}: Deine Handkarten:",
            f"  {cards}" if cards else "  -",
        ]
    )


def render_trick_resolved_summary(
    public_state_before: PublicState | None,
    resolved: TrickResolved,
) -> str:
    lines: list[str] = []
    if public_state_before is not None:
        lines.extend(format_public_deltas_for_cli(public_state_before, resolved.deltas))
    else:
        lines.append("Die Stichauflösung ist abgeschlossen.")

    if resolved.new_round_started:
        lines.extend(["", "== Neue Runde wurde ausgeteilt. =="])
    if resolved.game_finished:
        lines.extend(["", "== Das Spiel ist beendet. =="])
    return "\n".join(lines)


def render_public_state(state: PublicState) -> None:
    cli_state = CliState(public_state=state, mode=GameStateWaiting())
    print(render_game_overview(cli_state))


def render_handcards(state: PlayerState) -> None:
    print(render_own_hand(state))


def render_player_state(state: PlayerState) -> None:
    cli_state = CliState(
        own_player_id=state.self_player_id,
        public_state=state.public_state,
        mode=GameStateChooseCard(player_state=state),
    )
    print(render_game_choose_card(cli_state))


def render_trick_resolution(public_state_before: PublicState, message: TrickResolved) -> None:
    public_state_after = apply_deltas_public_state(public_state_before, message.deltas)
    cli_state = CliState(
        public_state=public_state_after,
        mode=GameStateTrickResolved(
            public_state_before=public_state_before,
            resolved=message,
        ),
    )
    print(render_game_trick_resolved(cli_state))
