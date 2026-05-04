import random
from typing import TypedDict

import pygame

import row_taker.gui.constants as c
from row_taker.gui.card import Card
from row_taker.gui.spielfeld import Spielfeld


class BotData(TypedDict):
    pos: tuple[float, float]
    color: tuple[int, int, int]


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

    hand: list[Card] = []
    for i in range(1, 11):
        h_card = Card(i + 30)
        h_card.scale(eff_width)
        h_card.y_hidden = float(screen_size[1] - h_card.base_height // 3)
        h_card.y_revealed = float(p_y + p_h + c.CARD_GAP)
        h_card.x = h_card.target_x = float(p_x + (i - 1) * (h_card.base_width + c.CARD_GAP))
        h_card.y = h_card.target_y = h_card.y_hidden
        hand.append(h_card)

    bots: list[BotData] = [
        {
            "pos": (float(screen_size[0] - 60), float(screen_size[1] // 4 * (i + 1))),
            "color": [(255, 100, 100), (100, 255, 100), (100, 100, 255)][i],
        }
        for i in range(3)
    ]

    placing_queue: list[tuple[Card, bool]] = []
    discarding_pool: list[Card] = []

    current_card: Card | None = None
    current_is_player: bool = False
    game_phase: str = "SELECTING"
    running: bool = True

    while running:
        mouse_pos = pygame.mouse.get_pos()
        cw = hand[0].base_width if hand else 50
        ch = hand[0].base_height if hand else 80

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

        # --- DRAWING ---
        spielfeld.draw(screen)
        for b in bots:
            pygame.draw.circle(screen, b["color"], (int(b["pos"][0]), int(b["pos"][1])), 25)

        for i, r_cards in enumerate(rows):
            if game_phase == "CHOOSING_ROW":
                color = (255, 255, 0) if row_rects[i].collidepoint(mouse_pos) else (150, 150, 0)
                pygame.draw.rect(screen, color, row_rects[i], 3)

            for j, c_obj in enumerate(r_cards):
                c_obj.target_x = float(p_x + i * (cw + c.CARD_GAP))
                y_off = (ch + c.CARD_GAP) if row_rects[i].collidepoint(mouse_pos) else (ch // 5)
                c_obj.target_y = float(p_y + j * y_off)
                c_obj.update()
                c_obj.draw(screen, mouse_pos)

        # Hand
        in_hand = mouse_pos[1] > (p_y + p_h)
        for h_c in hand:
            h_c.target_y = (
                h_c.y_revealed
                if (h_c.selected or (game_phase == "SELECTING" and in_hand))
                else h_c.y_hidden
            )
            h_c.update()
            h_c.draw(screen, mouse_pos)

        # Die Karte, die gerade "entscheidet", folgt der Maus
        if game_phase == "CHOOSING_ROW" and current_card:
            current_card.target_x, current_card.target_y = (
                float(mouse_pos[0] - cw // 2),
                float(mouse_pos[1] - ch // 2),
            )
            current_card.update()
            current_card.draw(screen)

        for d_c in discarding_pool:
            d_c.update()
            d_c.draw(screen)
        discarding_pool = [c_obj for c_obj in discarding_pool if c_obj.visible]

        pygame.display.flip()
        clock.tick(c.FPS)
    return 0


if __name__ == "__main__":
    run()
