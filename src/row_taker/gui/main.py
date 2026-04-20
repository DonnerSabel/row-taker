import time
import pygame

from row_taker.gui.card import Card
from row_taker.gui.constants import (
    BACKGROUND_COLOR,
    CARD_GAP,
    DEMO_CARD_VALUES,
    FPS,
    WINDOW_TITLE,
)
from row_taker.gui.spielfeld import Spielfeld


def create_demo_cards(window_width: int, window_height: int) -> list[Card]:
    deck = [Card(value) for value in DEMO_CARD_VALUES]

    if not deck:
        return []

    # Karten zuerst skalieren, um ihre Breite für die Zentrierung zu kennen
    for card in deck:
        card.scale(window_width, window_height)

    # 🔥 Perfekte Zentrierung berechnen
    card_width = deck[0].image.get_width()
    total_width = (len(deck) * card_width) + ((len(deck) - 1) * CARD_GAP)

    # Start-X ist die Hälfte des verbleibenden leeren Raums
    start_x = (window_width - total_width) // 2

    x_pos = start_x
    for card in deck:
        if card.image is None:
            continue

        # x und y auf das Zentrum setzen
        card.x = x_pos + card_width // 2
        card.target_x = card.x

        card.y = card.y_hidden
        card.target_y = card.y_hidden

        x_pos += card_width + CARD_GAP

    return deck


def run() -> int:
    pygame.init()
    spielfeld = Spielfeld()
    spielfeld.load_image()

    try:
        # 🔥 Fullscreen aktivieren und echte Auflösung abgreifen
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        window_width, window_height = screen.get_size()

        pygame.display.set_caption(WINDOW_TITLE)
        clock = pygame.time.Clock()

        # Generierung mit dynamischer Breite/Höhe
        deck = create_demo_cards(window_width, window_height)

        game_phase = "SELECTING"
        last_click_time = 0
        last_clicked_card = None
        DOUBLE_CLICK_TIME = 500

        trigger_line_y = window_height - (
            deck[0].image.get_height() if deck and deck[0].image else 200
        )

        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                # 🔥 Beenden nun auch über ESC möglich (wichtig im Fullscreen!)
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    running = False

                if event.type == pygame.KEYDOWN and event.key == pygame.K_w:
                    if game_phase == "LOCKED":
                        game_phase = "SELECTING"

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    current_time = pygame.time.get_ticks()
                    is_double_click = current_time - last_click_time < DOUBLE_CLICK_TIME

                    for card in reversed(deck):
                        if card.is_mouse_over(mouse_pos):
                            if is_double_click and last_clicked_card == card:
                                # Karte ist verriegelt, kann also nicht mehr selektiert werden
                                if game_phase == "SELECTING" and not card.played:
                                    card.phase = "WAITING"
                                    card.selection_time = time.time()
                                    card.played = True
                                    game_phase = "LOCKED"
                                    last_clicked_card = None
                            else:
                                last_click_time = current_time
                                last_clicked_card = card
                            break

            mouse_in_zone = mouse_pos[1] >= trigger_line_y

            for card in deck:
                if card.phase == "HAND":
                    if game_phase == "SELECTING" and mouse_in_zone:
                        card.target_y = card.y_revealed
                    else:
                        card.target_y = card.y_hidden

                card.update()

            if spielfeld.image is None:
                screen.fill(BACKGROUND_COLOR)
            else:
                # Hier spielfeld ggf. auch auf Fullscreen skalieren, falls es nicht schon passt
                spielfeld.draw(screen)

            # 🔥 Erlaube das Vergrößern der Hand-Karten nur, wenn wir gerade auswählen
            allow_hand_hover = game_phase == "SELECTING"

            for card in deck:
                card.draw(screen, mouse_pos, allow_hand_hover)

            pygame.display.flip()
            clock.tick(FPS)

        return 0
    finally:
        pygame.quit()
