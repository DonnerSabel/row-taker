from __future__ import annotations

import os
import random
import sys

from row_taker.cli.bot import bot_choose_random, create_players_with_bots
from row_taker.engine.game import resolve_round, setup_game, start_next_round_if_needed
from row_taker.engine.state import Card, GameState, Row


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if os.name != "nt" and not os.environ.get("TERM"):
        return
    os.system("cls" if os.name == "nt" else "clear")


def get_sorted_row_view(state: GameState) -> list[tuple[int, Row]]:
    return sorted(
        enumerate(state.rows),
        key=lambda pair: pair[1].cards[-1].value if pair[1].cards else 0,
    )


def render_state(state: GameState) -> None:
    print(f"Runde: {state.round_no}")
    print()
    print("Reihen:")

    sorted_view = get_sorted_row_view(state)

    for cli_index, (_, row) in enumerate(sorted_view, start=1):
        vals = " ".join(f"{c.value:>3}" for c in row.cards)
        pts = sum(c.points for c in row.cards)
        print(f"  Reihe {cli_index}: {vals:<25}  ({pts} Punkte)")

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

        sorted_view = get_sorted_row_view(state)

        if player_index >= len(player_names):
            cli_choice = random.randint(1, len(sorted_view))
            real_index, _ = sorted_view[cli_choice - 1]
            return real_index

        max_choice = len(sorted_view)
        s = input(f"Welche Reihe willst du nehmen? (1-{max_choice}) > ").strip()

        if s.isdigit():
            cli_choice = int(s)
            if 1 <= cli_choice <= max_choice:
                real_index, _ = sorted_view[cli_choice - 1]
                return real_index

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
        # Runde: jeder wählt eine Karte (verdeckt, Hotseat)
        selections: dict[int, Card] = {}
        for i in range(len(player_names)):
            selections[i] = choose_card_from_hand(state, i)
        for i in range(len(player_list) - len(player_names)):
            selections[len(player_names) + i] = bot_choose_random(state, len(player_names) + i)

        clear_screen()
        results = resolve_round(state, selections, choose_row_cli)

        render_state(state)
        print("Auflösung:")
        for r in results:
            p = state.players[r.player_index]
            if r.action == "placed":
                print(f"- {p.name} legt {r.card.value} an Reihe {r.row_index}.")
            elif r.action == "took_row_small":
                print(
                    f"- {p.name} nimmt Reihe {r.row_index} ({r.points_gained} Punkte) und startet mit {r.card.value}."
                )
            else:
                print(
                    f"- {p.name} füllt Reihe {r.row_index} (nimmt {r.points_gained} Punkte) und startet mit {r.card.value}."
                )

        # Neue Runde?
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
