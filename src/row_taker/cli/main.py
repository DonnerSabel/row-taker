from __future__ import annotations

import os
import sys

from row_taker.engine.game import resolve_round, setup_game, start_next_round_if_needed
from row_taker.engine.state import Card, GameState


def clear_screen() -> None:
    # Simple cross-platform clear
    os.system("cls" if os.name == "nt" else "clear")


def render_state(state: GameState) -> None:
    print(f"Runde: {state.round_no}")
    print()
    print("Reihen:")
    for i, row in enumerate(
        sorted(state.rows, key=lambda row: row.cards[-1].value if row.cards else 0)
    ):
        vals = " ".join(f"{c.value:>3}" for c in row.cards)
        pts = sum(c.points for c in row.cards)
        print(f"  [{i}] {vals:<25}  ({pts} Punkte)")
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
        s = input("Welche Reihe willst du nehmen? (0-3) > ").strip()
        if s.isdigit():
            idx = int(s)
            if 0 <= idx < 4:
                return idx
        print("Ungültig. Bitte 0-3 eingeben.")


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
    names = input("Spielernamen (kommagetrennt, 2-6) > ").strip()
    player_names = [n.strip() for n in names.split(",") if n.strip()]
    if not (2 <= len(player_names) <= 6):
        print("Bitte 2-6 Spielernamen angeben.")
        sys.exit(2)

    state = setup_game(player_names)

    while True:
        # Runde: jeder wählt eine Karte (verdeckt, Hotseat)
        selections: dict[int, Card] = {}
        for i in range(len(state.players)):
            selections[i] = choose_card_from_hand(state, i)

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


try:
    main()
except KeyboardInterrupt:
    clear_screen()
    print("Abbruch mit Strg+C!")
    sys.exit(0)
