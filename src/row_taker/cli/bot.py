from random import choice
from row_taker.engine.state import Card, GameState


def get_player_count():
    """Abfrage der Spieleranzahl aus der Konsole."""
    while True:
        try:
            count = int(input("Anzahl der Spieler: "))
            if count > 2:
                return count
            print("Bitte geben Sie eine Zahl größer als 2 ein.")
        except ValueError:
            print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")


def create_players_with_bots(player_names: list[str]) -> list[str]:
    """Erstellt Spieler aus player_names und füllt mit Bots auf."""
    player_count = get_player_count()
    num_human_players = len(player_names)
    num_bots = player_count - num_human_players

    player_list = list(player_names)

    if num_bots > 0:
        for i in range(num_bots):
            player_list.append(f"Bot_{i + 1}")
    elif num_bots < 0:
        print(f"Warnung: Mehr Namen (${num_human_players}) als Spieler (${player_count}).")
        player_list = player_list[:player_count]

    return player_list


def bot_choose_random(state: GameState, player_index: int) -> Card:
    """Einfacher Bot: wählt zufällig eine Karte aus der Hand."""
    p = state.players[player_index]
    return choice(p.hand)
