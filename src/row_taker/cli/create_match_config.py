from __future__ import annotations

from dataclasses import dataclass

from row_taker.protocol.messages import AssignSeatToClient, CreateLocalBotOnSeat, JoinLobby


@dataclass(slots=True, frozen=True)
class LocalLobbySetup:
    join_message: JoinLobby
    seat_assignments: tuple[AssignSeatToClient | CreateLocalBotOnSeat, ...]


def _prompt_player_count() -> int:
    while True:
        raw = input('Anzahl der Plätze (2-6) > ').strip()
        if raw.isdigit():
            count = int(raw)
            if 2 <= count <= 6:
                return count
        print('Bitte eine Zahl zwischen 2 und 6 eingeben.')


def _prompt_name(prompt: str, default: str) -> str:
    value = input(f'{prompt} [{default}] > ').strip()
    return value or default


def create_single_human_lobby_setup(client_id: str = 'client-0') -> LocalLobbySetup:
    seat_count = _prompt_player_count()
    human_name = _prompt_name('Name für den menschlichen Spieler', 'Spieler_1')
    assignments: list[AssignSeatToClient | CreateLocalBotOnSeat] = [AssignSeatToClient(seat_index=0, target_client_id=client_id)]

    for seat_index in range(1, seat_count):
        seat_no = seat_index + 1
        bot_name = _prompt_name(f'Name für Bot auf Platz {seat_no}', f'Bot_{seat_no}')
        assignments.append(CreateLocalBotOnSeat(seat_index=seat_index, display_name=bot_name))

    return LocalLobbySetup(join_message=JoinLobby(display_name=human_name), seat_assignments=tuple(assignments))
