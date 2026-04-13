import pygame

from row_taker.gui.card import Card
from row_taker.gui.constants import (
    BACKGROUND_COLOR,
    BOARD_PLAY_AREA_HEIGHT_RATIO,
    BOARD_PLAY_AREA_WIDTH_RATIO,
    BOARD_PLAY_AREA_X_RATIO,
    BOARD_PLAY_AREA_Y_RATIO,
    CARD_ASPECT_RATIO,
    CARD_GAP,
    CARD_SCALE,
    FPS,
    WINDOW_TITLE,
)
from row_taker.gui.spielfeld import Spielfeld


def create_demo_cards(window_width: int, window_height: int) -> list[Card]:
    rows = 4
    columns = 6

    # Calculate play area in pixels from ratios
    play_area_x = int(window_width * BOARD_PLAY_AREA_X_RATIO)
    play_area_y = int(window_height * BOARD_PLAY_AREA_Y_RATIO)
    play_area_width = int(window_width * BOARD_PLAY_AREA_WIDTH_RATIO)
    play_area_height = int(window_height * BOARD_PLAY_AREA_HEIGHT_RATIO)

    deck = [Card(value) for value in range(1, rows * columns + 1)]

    for card in deck:
        card.scale(window_width)

    if deck and deck[0].image is not None:
        # Calculate target dimensions to fit the board play area
        available_width = play_area_width - columns * CARD_GAP
        available_height = play_area_height - rows * CARD_GAP
        target_width_from_width = available_width / columns
        target_width_from_height = (available_height / rows) / CARD_ASPECT_RATIO
        target_width = min(target_width_from_width, target_width_from_height)

        # Calculate effective window width for scaling
        effective_window_width = int(target_width / CARD_SCALE)

        # Rescale cards
        for card in deck:
            card.scale(effective_window_width)

    card_width = (
        deck[0].image.get_width()
        if deck and deck[0].image is not None
        else int(window_width * CARD_SCALE)
    )
    card_height = (
        deck[0].image.get_height()
        if deck and deck[0].image is not None
        else int(card_width * CARD_ASPECT_RATIO)
    )
    total_height = rows * card_height + (rows + 1) * CARD_GAP
    y_start = play_area_y + max(CARD_GAP, (play_area_height - total_height) // 2)

    for index, card in enumerate(deck):
        if card.image is None:
            continue

        row = index // columns
        column = index % columns
        card.x = play_area_x + CARD_GAP + column * (card_width + CARD_GAP)
        card.y = y_start + row * (card_height + CARD_GAP)

    return deck


def run() -> int:
    pygame.init()
    spielfeld = Spielfeld()
    spielfeld.load_image()
    try:
        screen = pygame.display.set_mode(spielfeld.get_image_size())
        pygame.display.set_caption(WINDOW_TITLE)
        clock = pygame.time.Clock()

        deck = create_demo_cards(*spielfeld.get_image_size())

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
