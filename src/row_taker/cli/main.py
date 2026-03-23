from __future__ import annotations

import os
import random
import sys
from copy import deepcopy

from row_taker.cli.bot import create_players_with_bots
from row_taker.cli.row_display import build_row_display_mapping, format_results_for_cli
from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.game import resolve_round, setup_game, start_next_round_if_needed
from row_taker.engine.models import Card, PlayerID, RowID
from row_taker.engine.state import GameState, PlayerState
from row_taker.engine.views import build_player_state
from row_taker.engine_random.bot import choose_card_random, choose_row_random


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if os.name != "nt" and not os.environ.get("TERM"):
        return
    os.system("cls" if os.name == "nt" else "clear")


def _find_player_index_by_id(state: GameState, player_id: PlayerID) -> int:
    for index, player in enumerate(state.players):
        if player.player_id == player_id:
            return index
    raise ValueError(f"unknown player_id: {player_id!r}")


def _is_human_player(state: GameState, player_id: PlayerID, num_human_players: int) -> bool:
    player_index = _find_player_index_by_id(state, player_id)
    return player_index < num_human_players


def render_state(state: GameState) -> None:
    print(f"Runde: {state.round_no}")
    print(f"Stich: {state.trick_no}")
    print()
    print("Reihen:")

    mapping = build_row_display_mapping(state)

    for cli_row, state_row_index in enumerate(mapping.row_order, start=1):
        row = state.rows[state_row_index]
        vals = " ".join(f"{c.value:>3}" for c in row.cards)
        pts = row.points()
        print(f"  Reihe {cli_row}: {vals:<25}  ({pts} Punkte)")

    print()
    print("Scores:")
    for i, p in enumerate(state.players):
        print(f"  ({i}) {p.name}: {p.score}")
    print()


def render_player_state(state: PlayerState) -> None:
    print(f"Runde: {state.round_no}")
    print(f"Stich: {state.trick_no}")
    print()
    print("Reihen:")
    for index, row in enumerate(state.rows, start=1):
        vals = " ".join(f"{c.value:>3}" for c in row.cards)
        pts = row.points()
        print(f"  Reihe {index}: {vals:<25}  ({pts} Punkte)")
    print()
    print("Scores:")
    for i, p in enumerate(state.players):
        you = " <- du" if p.player_id == state.self_player_id else ""
        print(f"  ({i}) {p.name}: {p.score}, {p.hand_count} Karten{you}")
    print()


def choose_card_cli(state: PlayerState) -> PlayCardCommand:
    while True:
        clear_screen()
        render_player_state(state)

        own_name = next(
            p.name for p in state.players if p.player_id == state.self_player_id
        )
        print(f"{own_name}: Deine Handkarten:")
        print("  " + " ".join(f"|{c.value} {c.points * '🐮'}|" for c in state.hand))

        s = input("Wähle eine Karte (Zahl) > ").strip()
        if s.isdigit():
            v = int(s)
            for c in state.hand:
                if c.value == v:
                    return PlayCardCommand(
                        player_id=state.self_player_id,
                        card_value=c.value,
                    )

        input("Ungültige Wahl. Enter...")


def choose_row_cli_from_player_state(state: PlayerState) -> ChooseRowCommand:
    while True:
        clear_screen()
        render_player_state(state)

        own_name = next(
            p.name for p in state.players if p.player_id == state.self_player_id
        )
        pending_card_value = (
            state.phase_info.pending_card.value
            if state.phase_info.pending_card is not None
            else "?"
        )
        print(
            f"{own_name}: Deine Karte {pending_card_value} ist kleiner als alle Reihen."
        )

        allowed_row_ids = set(state.phase_info.selectable_row_ids)
        max_choice = len(state.rows)
        s = input(f"Welche Reihe willst du nehmen? (1-{max_choice}) > ").strip()

        if s.isdigit():
            cli_choice = int(s)
            if 1 <= cli_choice <= max_choice:
                row_id = state.rows[cli_choice - 1].row_id
                if row_id in allowed_row_ids:
                    return ChooseRowCommand(
                        player_id=state.self_player_id,
                        row_id=row_id,
                    )

        print(f"Ungültig. Bitte 1-{max_choice} eingeben.")
        input("Enter...")


def _choose_row_adapter(
    state: GameState,
    player_id: PlayerID,
    played_card: Card,
    *,
    num_human_players: int,
    rng: random.Random,
) -> RowID | ChooseRowCommand:
    player_state = build_player_state(state, player_id)

    if _is_human_player(state, player_id, num_human_players):
        return choose_row_cli_from_player_state(player_state)

    return choose_row_random(player_state, rng)


def _collect_selections_for_trick(
    state: GameState,
    *,
    num_human_players: int,
    rng: random.Random,
) -> dict[PlayerID, PlayCardCommand]:
    selections: dict[PlayerID, PlayCardCommand] = {}

    for player in state.players:
        player_state = build_player_state(state, player.player_id)

        if _is_human_player(state, player.player_id, num_human_players):
            cmd = choose_card_cli(player_state)
        else:
            cmd = choose_card_random(player_state, rng)

        selections[player.player_id] = cmd

    return selections


def main() -> None:
    rng = random.Random()

    clear_screen()
    print("Row-Taker – CLI (Hotseat)")
    print()
    names = input("Spielernamen (kommagetrennt, 1-6) > ").strip()
    player_names = [n.strip() for n in names.split(",") if n.strip()]
    if not (1 <= len(player_names) <= 6):
        print("Bitte 1-6 Spielernamen angeben.")
        sys.exit(2)

    player_list = create_players_with_bots(player_names)
    if not (2 <= len(player_list) <= 6):
        print("Die gesamte Spielerzahl muss zwischen 2 und 6 liegen.")
        sys.exit(2)

    state = setup_game(player_list, rng=rng)
    num_human_players = len(player_names)

    while True:
        selections = _collect_selections_for_trick(
            state,
            num_human_players=num_human_players,
            rng=rng,
        )

        clear_screen()
        state_before_round = deepcopy(state)
        results = resolve_round(
            state,
            selections,
            lambda current_state, player_id, played_card: _choose_row_adapter(
                current_state,
                player_id,
                played_card,
                num_human_players=num_human_players,
                rng=rng,
            ),
        )
        result_lines = format_results_for_cli(state_before_round, results)

        render_state(state)
        print("Auflösung:")
        for line in result_lines:
            print(line)

        started = start_next_round_if_needed(state)
        if started:
            print()
            print("== Neue Runde wurde ausgeteilt. ==")

        print()
        cont = input("Enter für nächsten Stich, 'q' zum Beenden > ").strip().lower()
        if cont == "q":
            break

    print()
    print("Endstand:")
    render_state(state)
    winner = min(state.players, key=lambda p: p.score)
    print(f"Gewonnen hat: {winner.name} (wenigste Punkte)")


def run() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        clear_screen()
        print("Abbruch mit Strg+C!")
        return 0
