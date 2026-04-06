from __future__ import annotations

from row_taker.engine.lobby.config import MatchConfig, SeatConfig


def _prompt_player_count() -> int:
    while True:
        raw = input("Anzahl der Plätze (2-6) > ").strip()
        if raw.isdigit():
            count = int(raw)
            if 2 <= count <= 6:
                return count
        print("Bitte eine Zahl zwischen 2 und 6 eingeben.")


def _prompt_name(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}] > ").strip()
    return value or default


def create_single_human_match_config() -> MatchConfig:
    seat_count = _prompt_player_count()
    human_name = _prompt_name("Name für den menschlichen Spieler", "Spieler_1")
    seats: list[SeatConfig] = [SeatConfig.human(0, human_name)]

    for seat_index in range(1, seat_count):
        seat_no = seat_index + 1
        bot_name = _prompt_name(f"Name für Bot auf Platz {seat_no}", f"Bot_{seat_no}")
        seats.append(SeatConfig.random_bot(seat_index, bot_name))

    return MatchConfig.from_seats(seats)
