MIN_PLAYERS = 2
MAX_PLAYERS = 6


def get_player_names() -> list[str]:
    """Abfrage der Spielernamen aus der Konsole."""
    while True:
        try:
            names = input(f"Spielernamen (kommagetrennt, 1-{MAX_PLAYERS}) > ").strip()
            player_names = [n.strip() for n in names.split(",") if n.strip()]
            if 1 <= len(player_names) <= MAX_PLAYERS:
                return player_names
            print(f"Bitte 1-{MAX_PLAYERS} Spielernamen angeben.")
        except Exception as e:
            print(f"Ungültige Eingabe: {e}. Bitte erneut versuchen.")


def get_player_count() -> int:
    """Abfrage der Spieleranzahl aus der Konsole."""
    while True:
        try:
            count = int(input(f"Anzahl der Spieler 2-{MAX_PLAYERS}: "))
            if not (MIN_PLAYERS <= count <= MAX_PLAYERS):
                return count
            print(f"Bitte {MIN_PLAYERS}-{MAX_PLAYERS} Spieler angeben.")
        except ValueError:
            print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")
