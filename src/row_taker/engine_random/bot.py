from random import choice

from row_taker.engine.state import Card, GameState


def bot_choose_random(state: GameState, player_index: int) -> Card:
    """Einfacher Bot: wählt zufällig eine Karte aus der Hand."""
    player = state.players[player_index]
    return choice(player.hand)
