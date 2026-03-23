from __future__ import annotations

import os
import random
import sys

from row_taker.cli.bot import create_players_with_bots
from row_taker.cli.row_display import build_row_display_mapping, format_results_for_cli
from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.game import resolve_round, setup_game, start_next_round_if_needed
from row_taker.engine.models import Card, PlayerID, RowID
from row_taker.engine.state import PlayerState
from row_taker.engine.views import build_player_state
from row_taker.engine_random.bot import choose_card_random, choose_row_random


def clear_screen() -> None:
    if not sys.stdout.isatty():
        return
    if os.name != "nt" and not os.environ.get("TERM"):
        return
    os.system("cls" if os.name == "nt" else "clear")


def _choose_display_player_id(state) -> PlayerID:
    return state.players[0].player_id


def _build_public_player_state(state) -> PlayerState:
    return build_player_state(state, _choose_display_player_id(state))


def _build_human_player_ids(state, num_human_players: int) -> set[PlayerID]:
    return {
        player.player_id
        for player in state.players[:num_human_players]
    }


def _is_human_player(player_id: PlayerID, human_player_ids: set[PlayerID]) -> bool:
    return player_id in human_player_ids


def render_public_state(state: PlayerState) -> None:
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

    mapping = build_row_display_mapping(state)

    for cli_row, state_row_index in enumerate(mapping.row_order, start=1):
        row = state.rows[state_row_index]
        vals = " ".join(f"{c.value:>3}" for c in row.cards)
        pts = row.points()
        print(f"  Reihe {cli_row}: {vals:<25}  ({pts} Punkte)")

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
    mapping = build_row_display_mapping(state)

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
        max_choice = mapping.max_cli_row()
        s = input(f"Welche Reihe willst du nehmen? (1-{max_choice}) > ").strip()

        if s.isdigit():
            cli_choice = int(s)
            if 1 <= cli_choice <= max_choice:
                state_row_index = mapping.to_state_index(cli_choice)
                row_id = state.rows[state_row_index].row_id
                if row_id in allowed_row_ids:
                    return ChooseRowCommand(
                        player_id=state.self_player_id,
                        row_id=row_id,
                    )

        print(f"Ungültig. Bitte 1-{max_choice} eingeben.")
        input("Enter...")


def _choose_row_adapter(
    state,
    player_id: PlayerID,
    played_card: Card,
    *,
    human_player_ids: set[PlayerID],
    rng: random.Random,
) -> RowID | ChooseRowCommand:
    player_state = build_player_state(state, player_id)

    if _is_human_player(player_id, human_player_ids):
        return choose_row_cli_from_player_state(player_state)

    return choose_row_random(player_state, rng)


def _collect_selections_for_trick(
    state,
    *,
    human_player_ids: set[PlayerID],
    rng: random.Random,
) -> dict[PlayerID, PlayCardCommand]:
    selections: dict[PlayerID, PlayCardCommand] = {}

    for player in state.players:
        player_state = build_player_state(state, player.player_id)

        if _is_human_player(player.player_id, human_player_ids):
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
    human_player_ids = _build_human_player_ids(state, len(player_names))

    while True:
        selections = _collect_selections_for_trick(
            state,
            human_player_ids=human_player_ids,
            rng=rng,
        )

        clear_screen()
        public_state_before_round = _build_public_player_state(state)

        results = resolve_round(
            state,
            selections,
            lambda current_state, player_id, played_card: _choose_row_adapter(
                current_state,
                player_id,
                played_card,
                human_player_ids=human_player_ids,
                rng=rng,
            ),
        )

        result_lines = format_results_for_cli(public_state_before_round, results)
        render_public_state(_build_public_player_state(state))

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
    render_public_state(_build_public_player_state(state))
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
