import pygame

from row_taker.gui.card import Card
from row_taker.gui.constants import (
    BACKGROUND_COLOR,
    CARD_GAP,
    DEMO_CARD_VALUES,
    FPS,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from row_taker.gui.spielfeld import Spielfeld


def create_demo_cards(window_width: int, window_height: int) -> list[Card]:
    deck = [Card(value) for value in DEMO_CARD_VALUES]

    for card in deck:
        card.scale(window_width)

    x_pos = CARD_GAP
    for card in deck:
        if card.image is None:
            continue
        card.x = x_pos
        card.y = window_height // 2 - card.image.get_height() // 2
        x_pos += card.image.get_width() + CARD_GAP

    return deck


def run() -> int:
    pygame.init()
    spielfeld = Spielfeld()
    spielfeld.load_image()
    try:
        screen = pygame.display.set_mode(spielfeld.get_image_size())
        pygame.display.set_caption(WINDOW_TITLE)
        clock = pygame.time.Clock()

        deck = create_demo_cards(WINDOW_WIDTH, WINDOW_HEIGHT)

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            if spielfeld.image is None:
                screen.fill(BACKGROUND_COLOR)
            else:
                spielfeld.draw(screen)

            for card in deck:
                card.draw(screen)

            pygame.display.flip()
            clock.tick(FPS)

        return 0
    finally:
        pygame.quit()


if __name__ == "__main__":
    exit(run())
