import os
import random
import sys
from copy import deepcopy

from row_taker.cli.bot import create_players_with_bots
from row_taker.cli.row_display import build_row_display_mapping, format_results_for_cli
from row_taker.engine.game import resolve_round, setup_game, start_next_round_if_needed
from row_taker.engine.state import Card, GameState
from row_taker.engine_random.bot import bot_choose_random


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if os.name != "nt" and not os.environ.get("TERM"):
        return
    os.system("cls" if os.name == "nt" else "clear")


def render_state(state: GameState) -> None:
    print(f"Runde: {state.round_no}")
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


def choose_row_cli(state: GameState, player_index: int, played_card: Card) -> int:
    while True:
        render_state(state)
        p = state.players[player_index]
        print(f"{p.name}: Deine Karte {played_card.value} ist kleiner als alle Reihen.")

        mapping = build_row_display_mapping(state)

        if player_index >= len(player_names):
            cli_choice = random.randint(1, mapping.max_cli_row())
            return mapping.to_state_index(cli_choice)

        max_choice = mapping.max_cli_row()
        s = input(f"Welche Reihe willst du nehmen? (1-{max_choice}) > ").strip()

        if s.isdigit():
            cli_choice = int(s)
            if 1 <= cli_choice <= max_choice:
                return mapping.to_state_index(cli_choice)

        print(f"Ungültig. Bitte 1-{max_choice} eingeben.")


def choose_card_from_hand(state: GameState, player_index: int) -> Card:
    p = state.players[player_index]
    while True:
        clear_screen()
        render_state(state)
        print(f"{p.name}: Deine Handkarten:")
        print("  " + " ".join(f"|{c.value} {c.points * '🐮'}|" for c in p.hand))
        s = input("Wähle eine Karte (Zahl) > ").strip()
        if s.isdigit():
            v = int(s)
            for c in p.hand:
                if c.value == v:
                    return c
        input("Ungültige Wahl. Enter...")


def main() -> None:
    clear_screen()
    print("Row-Taker – CLI (Hotseat)")
    print()
    names = input("Spielernamen (kommagetrennt, 1-6) > ").strip()
    global player_names
    player_names = [n.strip() for n in names.split(",") if n.strip()]
    if not (1 <= len(player_names) <= 6):
        print("Bitte 1-6 Spielernamen angeben.")
        sys.exit(2)

    player_list = create_players_with_bots(player_names)
    state = setup_game(player_list)

    while True:
        selections: dict[int, Card] = {}

        for i in range(len(player_names)):
            selections[i] = choose_card_from_hand(state, i)
        for i in range(len(player_list) - len(player_names)):
            selections[len(player_names) + i] = bot_choose_random(state, len(player_names) + i)

        clear_screen()
        state_before_round = deepcopy(state)
        results = resolve_round(state, selections, choose_row_cli)
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
        cont = input("Enter für nächste Runde, 'q' zum Beenden > ").strip().lower()
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
