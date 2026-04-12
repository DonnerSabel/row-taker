from __future__ import annotations

from dataclasses import dataclass

from row_taker.cli.row_display import build_row_display_mapping, format_public_deltas_for_cli
from row_taker.cli.state_models import CliState, GameScreen, LobbyScreen, TrickResolvedModal, UiMessage
from row_taker.engine.game.public_state_ops import apply_deltas_public_state
from row_taker.engine.game.state import PlayerState, PublicState
from row_taker.protocol.messages import LobbyParticipantView, LobbySeatView, TrickResolved, TrickRevealed


@dataclass(frozen=True, slots=True)
class ScreenView:
    body: str
    prompt: str | None


def build_view(state: CliState) -> ScreenView:
    if state.session_error is not None:
        return ScreenView(body=render_session_error(state.session_error), prompt=determine_prompt(state))
    body = render_main_screen(state)
    if state.flash_message is not None:
        body = "\n\n".join([body, render_flash_message(state.flash_message)])
    if state.modal is not None:
        body = "\n\n".join([body, render_modal(state)])
    return ScreenView(body=body, prompt=determine_prompt(state))


def get_prompt(state: CliState) -> str | None:
    return build_view(state).prompt


def render_screen(state: CliState) -> str:
    return build_view(state).body


def determine_prompt(state: CliState) -> str | None:
    if state.session_error is not None:
        return "Weiter mit Enter > " if state.exit_on_ack else None
    if state.modal is not None:
        return "Weiter mit Enter > "
    match state.screen:
        case LobbyScreen(kind="main"):
            return "Auswahl > "
        case LobbyScreen(kind="rename"):
            return "Neuer Anzeigename > "
        case LobbyScreen(kind="seat_edit", seat_index=seat_index):
            return f"Platz {seat_index} > "
        case LobbyScreen(kind="bot_name"):
            return "Bot-Name > "
        case GameScreen(kind="waiting"):
            return None
        case GameScreen(kind="choose_card"):
            return "Karte > "
        case GameScreen(kind="choose_row"):
            return "Reihe > "
        case GameScreen(kind="ended"):
            return "Weiter mit Enter > "
    raise TypeError(f"unsupported screen: {state.screen!r}")


def render_main_screen(state: CliState) -> str:
    match state.screen:
        case LobbyScreen(kind="main"):
            return render_lobby_main(state)
        case LobbyScreen(kind="rename"):
            return render_lobby_rename(state)
        case LobbyScreen(kind="seat_edit"):
            return render_lobby_seat_edit(state)
        case LobbyScreen(kind="bot_name"):
            return render_lobby_bot_name(state)
        case GameScreen(kind="waiting"):
            return render_game_waiting(state)
        case GameScreen(kind="choose_card"):
            return render_game_choose_card(state)
        case GameScreen(kind="choose_row"):
            return render_game_choose_row(state)
        case GameScreen(kind="ended"):
            return render_game_ended(state)
    raise TypeError(f"unsupported screen: {state.screen!r}")


def render_session_error(message: str) -> str:
    return "\n".join(["Spielabbruch", "-----------", message])


def render_flash_message(message: UiMessage) -> str:
    title = "Fehler" if message.level == "error" else "Hinweis"
    return "\n".join([f"{title}: {message.text}"])


def render_modal(state: CliState) -> str:
    modal = state.modal
    if not isinstance(modal, TrickResolvedModal):
        raise TypeError(f"unsupported modal: {modal!r}")
    lines = [
        "Stich aufgelöst",
        "---------------",
        "",
        render_trick_resolved_summary(modal.public_state_before, modal.resolved),
    ]
    return "\n".join(lines)


def render_lobby_main(state: CliState) -> str:
    return "\n".join(
        [
            render_lobby_overview(state),
            "",
            "Menü:",
            "  n = Name ändern",
            "  0,1,2,3... = Platz editieren",
            "  g = Spiel starten",
        ]
    )


def render_lobby_rename(state: CliState) -> str:
    return "\n".join(
        [
            render_lobby_overview(state),
            "",
            "Name ändern",
            "-----------",
            "Bitte neuen Anzeigenamen eingeben.",
        ]
    )


def render_lobby_seat_edit(state: CliState) -> str:
    screen = state.screen
    if not isinstance(screen, LobbyScreen) or screen.kind != "seat_edit" or screen.seat_index is None:
        raise TypeError("expected seat_edit screen")
    return "\n".join(
        [
            render_lobby_overview_with_highlight(state, screen.seat_index),
            "",
            f"Platz {screen.seat_index} bearbeiten",
            "-------------------------",
            "  m = mich setzen",
            "  b = Bot setzen/umbenennen",
            "  c = Platz leeren",
            "  x = zurück",
        ]
    )


def render_lobby_bot_name(state: CliState) -> str:
    screen = state.screen
    if not isinstance(screen, LobbyScreen) or screen.kind != "bot_name" or screen.seat_index is None:
        raise TypeError("expected bot_name screen")
    current_name = _current_bot_name(state, screen.seat_index)
    return "\n".join(
        [
            render_lobby_overview_with_highlight(state, screen.seat_index),
            "",
            f"Bot für Platz {screen.seat_index}",
            "-------------------",
            f"Aktueller/Vorgeschlagener Name: {current_name}",
            "Neuen Bot-Namen eingeben.",
            "Leere Eingabe übernimmt den vorgeschlagenen Namen.",
            "x bricht ab.",
        ]
    )


def render_lobby_overview(state: CliState) -> str:
    lobby = state.lobby_view
    if lobby is None:
        return "\n".join(["Lobby", "-----", "Noch keine Lobby-Daten vorhanden."])
    lines = ["Lobby", "-----"]
    if lobby.server_endpoint:
        lines.extend(["", f"Server: {lobby.server_endpoint}"])
    lines.extend(["", "Plätze:"])
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
        lines.append(render_lobby_participant_line(state, participant))
    return "\n".join(lines)


def render_lobby_overview_with_highlight(state: CliState, selected_seat_index: int) -> str:
    lobby = state.lobby_view
    if lobby is None:
        return render_lobby_overview(state)
    lines = ["Lobby", "-----"]
    if lobby.server_endpoint:
        lines.extend(["", f"Server: {lobby.server_endpoint}"])
    lines.extend(["", "Plätze:"])
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
        lines.append(render_lobby_participant_line(state, participant))
    return "\n".join(lines)


def render_lobby_participant_line(state: CliState, participant: LobbyParticipantView) -> str:
    position = f"Platz {participant.seat_index}" if participant.seat_index is not None else "nicht gesetzt"
    marker = " <- du" if participant.client_id == state.own_client_id else ""
    return f"  {participant.display_name} ({participant.participant_kind}, {position}){marker}"


def render_lobby_seat_line(state: CliState, seat_index: int, seat: LobbySeatView) -> str:
    return f"  [{seat_index}] {_describe_lobby_seat(state, seat)}"


def _describe_lobby_seat(state: CliState, seat: LobbySeatView) -> str:
    if seat.occupant_display_name is None:
        return "(leer)"
    label = f"{seat.occupant_display_name} ({seat.occupant_kind})"
    if seat.occupant_client_id == state.own_client_id:
        label += " <- du"
    return label


def _current_bot_name(state: CliState, seat_index: int) -> str:
    lobby = state.lobby_view
    if lobby is not None:
        for seat in lobby.seats:
            if seat.seat_index == seat_index and seat.occupant_kind == "bot" and seat.occupant_display_name:
                return seat.occupant_display_name
    return f"Bot_{seat_index}"


def render_game_waiting(state: CliState) -> str:
    lines = [render_game_overview(state)]
    revealed = render_revealed_trick(state.revealed_trick, own_player_id=state.own_player_id)
    if revealed is not None:
        lines.extend(["", revealed])
    lines.extend(["", "Warten auf andere Spieler..."])
    return "\n".join(lines)


def render_game_choose_card(state: CliState) -> str:
    screen = state.screen
    if not isinstance(screen, GameScreen) or screen.kind != "choose_card" or screen.player_state is None:
        raise TypeError("expected choose_card screen")
    lines = [
        render_game_overview(state),
        "",
        render_own_hand(screen.player_state),
        "",
        "Du bist dran.",
        "Wähle eine Karte aus deiner Hand.",
    ]
    return "\n".join(lines)


def render_game_choose_row(state: CliState) -> str:
    screen = state.screen
    if not isinstance(screen, GameScreen) or screen.kind != "choose_row" or screen.player_state is None:
        raise TypeError("expected choose_row screen")
    mapping = build_row_display_mapping(screen.player_state.public_state)
    pending_card_value = screen.player_state.pending_card_value()
    pending_card_text = "?" if pending_card_value is None else str(pending_card_value)
    lines = [render_game_overview(state)]
    revealed = render_revealed_trick(state.revealed_trick, own_player_id=state.own_player_id)
    if revealed is not None:
        lines.extend(["", revealed])
    lines.extend(
        [
            "",
            render_own_hand(screen.player_state),
            "",
            f"Deine Karte {pending_card_text} ist kleiner als alle Reihen.",
            f"Bitte wähle eine Reihe zwischen 1 und {mapping.max_cli_row()}.",
        ]
    )
    return "\n".join(lines)


def render_game_ended(state: CliState) -> str:
    lines = ["Spiel beendet", "-------------"]
    if state.public_state is not None:
        lines.extend(["", render_game_overview(state)])
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


def render_revealed_trick(revealed: TrickRevealed | None, *, own_player_id) -> str | None:
    if revealed is None:
        return None
    lines = ["Gespielte Karten:"]
    for card in revealed.played_cards:
        marker = " <- du" if card.player_id == own_player_id else ""
        lines.append(f"  {card.card_value:>3}  {card.player_name}{marker}")
    if revealed.active_player_id is not None:
        chooser_name = next(
            (card.player_name for card in revealed.played_cards if card.player_id == revealed.active_player_id),
            str(revealed.active_player_id),
        )
        if revealed.pending_card_value is None:
            lines.append(f"{chooser_name} muss eine Reihe wählen.")
        else:
            lines.append(f"{chooser_name} muss für Karte {revealed.pending_card_value} eine Reihe wählen.")
    return "\n".join(lines)


def render_own_hand(player_state: PlayerState) -> str:
    cards = " ".join(f"|{card.value} {card.bullheads * '🐮'}|" for card in player_state.hand)
    return "\n".join([
        f"{player_state.self_player_name()}: Deine Handkarten:",
        f"  {cards}" if cards else "  -",
    ])


def render_trick_resolved_summary(public_state_before: PublicState | None, resolved: TrickResolved) -> str:
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
    cli_state = CliState(public_state=state, screen=GameScreen(kind="waiting"))
    print(render_game_overview(cli_state))


def render_handcards(state: PlayerState) -> None:
    print(render_own_hand(state))


def render_player_state(state: PlayerState) -> None:
    cli_state = CliState(
        own_player_id=state.self_player_id,
        public_state=state.public_state,
        screen=GameScreen(kind="choose_card", player_state=state),
    )
    print(render_game_choose_card(cli_state))


def render_trick_resolution(public_state_before: PublicState, message: TrickResolved) -> None:
    public_state_after = apply_deltas_public_state(public_state_before, message.deltas)
    cli_state = CliState(
        public_state=public_state_after,
        modal=TrickResolvedModal(public_state_before=public_state_before, resolved=message),
        screen=GameScreen(kind="waiting"),
    )
    print(render_modal(cli_state))
