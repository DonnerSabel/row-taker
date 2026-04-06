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


def _prompt_client_kind(seat_no: int) -> str:
    while True:
        value = input(f"Platz {seat_no} Typ [h=Human, b=Random Bot] > ").strip().lower()
        if value in {"h", "b"}:
            return value
        print("Bitte h oder b eingeben.")


def _prompt_name(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}] > ").strip()
    return value or default


def create_match_config() -> MatchConfig:
    seat_count = _prompt_player_count()
    seats: list[SeatConfig] = []
    bot_counter = 1

    for seat_index in range(seat_count):
        seat_no = seat_index + 1
        kind = _prompt_client_kind(seat_no)

        if kind == "h":
            name = _prompt_name(f"Name für Platz {seat_no}", f"Spieler_{seat_no}")
            seats.append(SeatConfig.human(seat_index, name))
            continue

        name = _prompt_name(f"Name für Bot auf Platz {seat_no}", f"Bot_{bot_counter}")
        bot_counter += 1
        seats.append(SeatConfig.random_bot(seat_index, name))

    return MatchConfig.from_seats(seats)
