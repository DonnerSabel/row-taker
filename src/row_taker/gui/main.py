import random
from typing import TypedDict

import pygame

from row_taker.engine.game.cards import Card
from row_taker.gui.card import CardSprite
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
    HANDCARD_GAP,
    HANDCARD_SCALE,
    WINDOW_TITLE,
    OFFSET_HANDCARD_x,
)
from row_taker.gui.spielfeld import Spielfeld


def create_demo_cards(window_width: int, window_height: int) -> tuple[list[CardSprite], list[CardSprite]]:
    board_rows = 6
    board_columns = 4
    hand_columns = 10

    # Calculate play area in pixels from ratios
    play_area_x = int(window_width * BOARD_PLAY_AREA_X_RATIO)
    play_area_y = int(window_height * BOARD_PLAY_AREA_Y_RATIO)
    play_area_width = int(window_width * BOARD_PLAY_AREA_WIDTH_RATIO)
    play_area_height = int(window_height * BOARD_PLAY_AREA_HEIGHT_RATIO)

    # Hand area below play area
    hand_y = play_area_y + play_area_height

    deck = [
        CardSprite(Card(value))
        for value in range(1, board_rows * board_columns + hand_columns + 1)
    ]

    for card_sprite in deck:
        card_sprite.scale(window_width)

    if deck and deck[0].image is not None:
        # Calculate target dimensions to fit the board play area.
        max_columns = max(board_columns, hand_columns)
        available_width = play_area_width - max_columns * CARD_GAP
        available_height = play_area_height - board_rows * CARD_GAP
        target_width_from_width = available_width / max_columns
        target_width_from_height = (available_height / board_rows) / CARD_ASPECT_RATIO
        target_width = min(target_width_from_width, target_width_from_height)

        # Calculate effective window width for CardSprite.scale().
        effective_window_width = int(target_width / CARD_SCALE)

        # Rescale cards so the board layout fits the background image.
        for card_sprite in deck:
            card_sprite.scale(effective_window_width)

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

    for index, card_sprite in enumerate(board_cards):
        if card_sprite.image is None:
            continue

        row = index // board_columns
        column = index % board_columns
        card_sprite.move_to(
            play_area_x + CARD_GAP + column * (card_width + CARD_GAP),
            y_start + row * (card_height // 5),
        )

    # Hand cards
    hand_cards = deck[board_rows * board_columns :]

    # Rescale hand cards with HANDCARD_SCALE
    handcard_window_width = int(window_width * HANDCARD_SCALE / CARD_SCALE)
    for card in hand_cards:
        card.scale(handcard_window_width)

    handcard_width = (
        hand_cards[0].image.get_width()
        if hand_cards and hand_cards[0].image is not None
        else int(window_width * HANDCARD_SCALE)
    )
    hand_y_start = hand_y

    for index, card_sprite in enumerate(hand_cards):
        if card_sprite.image is None:
            continue

        card_sprite.move_to(
            play_area_x + OFFSET_HANDCARD_x + index * (handcard_width + HANDCARD_GAP),
            hand_y_start,
        )

    return board_cards, hand_cards, play_area_x, play_area_y, card_width, card_height, board_columns


def run() -> int:
    pygame.init()
    spielfeld = Spielfeld()
    spielfeld.load_image()
    screen_size = spielfeld.get_image_size()
    screen = pygame.display.set_mode(screen_size)
    pygame.display.set_caption(c.WINDOW_TITLE)
    clock = pygame.time.Clock()

    p_x, p_y = (
        int(screen_size[0] * c.BOARD_PLAY_AREA_X_RATIO),
        int(screen_size[1] * c.BOARD_PLAY_AREA_Y_RATIO),
    )
    p_w, p_h = (
        int(screen_size[0] * c.BOARD_PLAY_AREA_WIDTH_RATIO),
        int(screen_size[1] * c.BOARD_PLAY_AREA_HEIGHT_RATIO),
    )
    eff_width = int((p_w - 11 * c.CARD_GAP) / 10 / c.CARD_SCALE)

    rows: list[list[Card]] = []
    for n in random.sample(range(1, 105), 4):
        card_obj = Card(n)
        card_obj.scale(eff_width)
        card_obj.phase = "BOARD"
        rows.append([card_obj])
    rows.sort(key=lambda r: r[-1].number)

        (
            board_cards,
            hand_cards,
            play_area_x,
            play_area_y,
            card_width,
            card_height,
            board_columns,
        ) = create_demo_cards(*spielfeld.get_image_size())

    current_card: Card | None = None
    current_is_player: bool = False
    game_phase: str = "SELECTING"
    running: bool = True

            for event in pygame.event.get():
                # 🔥 Beenden nun auch über ESC möglich (wichtig im Fullscreen!)
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    for card_sprite in hand_cards:
                        if card_sprite.is_mouse_over(mouse_pos):
                            card_sprite.selected = not card_sprite.selected
                            break

            mouse_pos = pygame.mouse.get_pos()

            # Determine which column the mouse is over (based on x position)
            hovered_column = None
            if (
                play_area_x
                <= mouse_pos[0]
                <= play_area_x + card_width * board_columns + CARD_GAP * (board_columns + 1)
            ):
                # Calculate which column based on x position
                relative_x = mouse_pos[0] - play_area_x
                col = (relative_x - CARD_GAP) // (card_width + CARD_GAP)
                if 0 <= col < board_columns:
                    hovered_column = col

            # Update board card positions based on hover state
            play_area_height = int(spielfeld.get_image_size()[1] * BOARD_PLAY_AREA_HEIGHT_RATIO)
            total_height = 6 * card_height + (6 + 1) * CARD_GAP
            y_start = play_area_y + max(CARD_GAP, (play_area_height - total_height) // 2)

            for index, card_sprite in enumerate(board_cards):
                row = index // board_columns
                column = index % board_columns
                x = play_area_x + CARD_GAP + column * (card_width + CARD_GAP)
                if hovered_column == column:
                    # Spread cards vertically with full height when hovering over this column.
                    y = y_start + row * (card_height + CARD_GAP)
                else:
                    # Stack cards with 1/5 offset when not hovering.
                    y = y_start + row * (card_height // 5)
                card_sprite.move_to(x, y)

        row_rects: list[pygame.Rect] = [
            pygame.Rect(p_x + i * (cw + c.CARD_GAP), p_y, cw, p_h) for i in range(4)
        ]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_phase == "SELECTING":
                    for h_c in reversed(hand):
                        if h_c.is_mouse_over(mouse_pos):
                            for other in hand:
                                other.selected = False
                            h_c.selected = True
                            game_phase = "LOCKED"
                            break

                # INTERAKTIVE WAHL
                elif game_phase == "CHOOSING_ROW":
                    for i, r_rect in enumerate(row_rects):
                        if r_rect.collidepoint(mouse_pos):
                            # Reihe räumen
                            for c_rem in rows[i]:
                                c_rem.fly_off_screen()
                                discarding_pool.append(c_rem)
                            # Karte setzen
                            if current_card:
                                rows[i] = [current_card]
                                current_card = None
                            rows.sort(key=lambda r: r[-1].number)
                            game_phase = "ANIMATING"  # Zurück zur Animation der restlichen Karten
                            break

            if (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_SPACE
                and game_phase == "LOCKED"
            ):
                game_phase = "ANIMATING"
                temp_played: list[tuple[Card, bool]] = []
                for h_c in hand[:]:
                    if h_c.selected:
                        h_c.selected = False
                        temp_played.append((h_c, True))
                        hand.remove(h_c)
                        break
                for b in bots:
                    bc = Card(random.randint(1, 104))
                    bc.scale(eff_width)
                    bc.spawn_from(*b["pos"])
                    temp_played.append((bc, False))
                temp_played.sort(key=lambda x: x[0].number)
                placing_queue = temp_played

        # --- REPARIERTE ANIMATIONS-STEUERUNG ---
        if game_phase == "ANIMATING":
            if current_card is None:
                if placing_queue:
                    # Nächste Karte prüfen
                    next_c, next_is_p = placing_queue[0]

                    # Passt sie in eine Reihe?
                    can_place = False
                    for r_cards in rows:
                        if next_c.number > r_cards[-1].number:
                            can_place = True
                            break

                    if not can_place:
                        if next_is_p:
                            # STOP! Spieler muss wählen
                            current_card, current_is_player = placing_queue.pop(0)
                            game_phase = "CHOOSING_ROW"
                        else:
                            # Bot wählt sofort
                            current_card, current_is_player = placing_queue.pop(0)
                            t_idx = random.randint(0, 3)
                            for c_rem in rows[t_idx]:
                                c_rem.fly_off_screen()
                                discarding_pool.append(c_rem)
                            rows[t_idx] = [current_card]
                            current_card = None
                            rows.sort(key=lambda r: r[-1].number)
                    else:
                        # Normales Anlegen
                        current_card, current_is_player = placing_queue.pop(0)
                        best_idx, min_diff = -1, 999
                        for i, r_cards in enumerate(rows):
                            diff = current_card.number - r_cards[-1].number
                            if 0 < diff < min_diff:
                                min_diff, best_idx = diff, i

                        rows[best_idx].append(current_card)
                        if len(rows[best_idx]) > 5:
                            for c_rem in rows[best_idx][:-1]:
                                c_rem.fly_off_screen()
                                discarding_pool.append(c_rem)
                            rows[best_idx] = [rows[best_idx][-1]]
                        rows.sort(key=lambda r: r[-1].number)
                else:
                    game_phase = "SELECTING"
            else:
                # Warten bis Animation der aktuellen Karte fertig ist
                if current_card.is_at_target():
                    current_card = None

            for card_sprite in board_cards:
                card_sprite.draw(screen, mouse_pos)

            for card_sprite in hand_cards:
                card_sprite.draw(screen, mouse_pos)

            for j, c_obj in enumerate(r_cards):
                c_obj.target_x = float(p_x + i * (cw + c.CARD_GAP))
                y_off = (ch + c.CARD_GAP) if row_rects[i].collidepoint(mouse_pos) else (ch // 5)
                c_obj.target_y = float(p_y + j * y_off)
                c_obj.update()
                c_obj.draw(screen, mouse_pos)

        return 0

    finally:
        pygame.quit()
