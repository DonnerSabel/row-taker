import pygame

from row_taker.gui.card import Card
from row_taker.gui.constants import (
    BACKGROUND_COLOR,
    DEMO_CARD_VALUES,
    FPS,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    OFFSET_Xr,
    OFFSET_Xl,
    OFFSET_Yo,
)
from row_taker.gui.spielfeld import Spielfeld


def create_demo_cards(
    window_width: int, window_height: int
) -> list[Card]:  # TODO: (Anid) Carten von Engine State verwenden
    deck = [Card(value) for value in DEMO_CARD_VALUES]

    for card in deck:
        card.scale(window_width)

    x_pos = OFFSET_Xl
    for card in deck:
        if card.image is None:
            continue
        card.x = x_pos
        card.y = OFFSET_Yo
        CARD_GAP = (
            (
                WINDOW_WIDTH  # TODO: (Andi) Aufbau kartendeck abhängig nur vom Spielfeld und nicht vom gesamten Fenster.
                - OFFSET_Xl
                - (card.image.get_width() * DEMO_CARD_VALUES.__len__())
                - OFFSET_Xr
            )
            / (DEMO_CARD_VALUES.__len__() - 1)
        )
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

            mouse_pos = pygame.mouse.get_pos()  # ✅ Mausposition

            if spielfeld.image is None:
                screen.fill(BACKGROUND_COLOR)
            else:
                spielfeld.draw(screen)

            for card in deck:
                card.draw(screen, mouse_pos)  # ✅ Hover funktioniert

            pygame.display.flip()
            clock.tick(FPS)

        return 0
    finally:
        pygame.quit()
