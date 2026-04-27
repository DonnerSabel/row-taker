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


def create_demo_cards(window_width: int, window_height: int) -> tuple[list[Card], list[Card]]:
    board_rows = 4
    board_columns = 6
    hand_columns = 10

    # Calculate play area in pixels from ratios
    play_area_x = int(window_width * BOARD_PLAY_AREA_X_RATIO)
    play_area_y = int(window_height * BOARD_PLAY_AREA_Y_RATIO)
    play_area_width = int(window_width * BOARD_PLAY_AREA_WIDTH_RATIO)
    play_area_height = int(window_height * BOARD_PLAY_AREA_HEIGHT_RATIO)

    # Hand area below play area
    hand_y = play_area_y + play_area_height + CARD_GAP

    deck = [Card(value) for value in range(1, board_rows * board_columns + hand_columns + 1)]

    for card in deck:
        card.scale(window_width)

    if deck and deck[0].image is not None:
        # Calculate target dimensions to fit the board play area
        max_columns = max(board_columns, hand_columns)
        available_width = play_area_width - max_columns * CARD_GAP
        available_height = play_area_height - board_rows * CARD_GAP
        target_width_from_width = available_width / max_columns
        target_width_from_height = (available_height / board_rows) / CARD_ASPECT_RATIO
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

    # Board cards
    board_cards = deck[: board_rows * board_columns]
    total_height = board_rows * card_height + (board_rows + 1) * CARD_GAP
    y_start = play_area_y + max(CARD_GAP, (play_area_height - total_height) // 2)

    for index, card in enumerate(board_cards):
        if card.image is None:
            continue

        row = index // board_columns
        column = index % board_columns
        card.x = play_area_x + CARD_GAP + column * (card_width + CARD_GAP)
        card.y = y_start + row * (card_height + CARD_GAP)

    # Hand cards
    hand_cards = deck[board_rows * board_columns :]
    hand_y_start = hand_y + CARD_GAP
    for index, card in enumerate(hand_cards):
        if card.image is None:
            continue

        card.x = play_area_x + CARD_GAP + index * (card_width + CARD_GAP)
        card.y = hand_y_start

    return board_cards, hand_cards


def run() -> int:
    pygame.init()
    spielfeld = Spielfeld()
    spielfeld.load_image()
    try:
        screen = pygame.display.set_mode(spielfeld.get_image_size())
        pygame.display.set_caption(WINDOW_TITLE)
        clock = pygame.time.Clock()

        board_cards, hand_cards = create_demo_cards(*spielfeld.get_image_size())

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    for card in hand_cards:
                        if card.is_mouse_over(mouse_pos):
                            card.selected = not card.selected
                            break  # Only select one at a time?

            mouse_pos = pygame.mouse.get_pos()  # ✅ Mausposition

            if spielfeld.image is None:
                screen.fill(BACKGROUND_COLOR)
            else:
                spielfeld.draw(screen)

            for card in board_cards:
                card.draw(screen, mouse_pos)  # ✅ Hover funktioniert

            for card in hand_cards:
                card.draw(screen, mouse_pos)  # Hand cards also hover

            pygame.display.flip()
            clock.tick(FPS)

        return 0
    finally:
        pygame.quit()
