from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame

from row_taker.gui.board_layout import (
    BoardGeometry,
    CardPlacement,
    compute_board_geometry,
    hand_card_placements,
    row_card_placements,
)

WINDOW_TITLE = "Row-Taker Layout Debug"
DEFAULT_SIZE = (1200, 800)
FPS = 30

COLOR_MAIN = pygame.Color(255, 255, 255)
COLOR_ROW_AREA = pygame.Color(80, 220, 255)
COLOR_OPPONENT_AREA = pygame.Color(255, 190, 70)
COLOR_STATS = pygame.Color(255, 90, 210)
COLOR_HAND = pygame.Color(110, 255, 110)
COLOR_OVERLAY = pygame.Color(180, 140, 255)
COLOR_ROW_COLUMN = pygame.Color(255, 255, 60)
COLOR_ROW_CARD = pygame.Color(20, 240, 90)
COLOR_HAND_CARD = pygame.Color(255, 120, 40)
COLOR_STAGED_CARD = pygame.Color(80, 170, 255)
COLOR_CIRCLE = pygame.Color(255, 80, 80)
COLOR_TEXT_BG = pygame.Color(0, 0, 0, 155)


class LayoutDebugApp:
    def __init__(self) -> None:
        self._running = True
        self._opponent_count = 3
        self._hand_card_count = 10
        self._row_card_count = 5
        self._show_labels = True
        self._screen: pygame.Surface | None = None
        self._font: pygame.font.Font | None = None
        self._small_font: pygame.font.Font | None = None
        self._clock: pygame.time.Clock | None = None

    def run(self) -> int:
        pygame.init()
        try:
            pygame.display.set_caption(WINDOW_TITLE)
            self._screen = pygame.display.set_mode(DEFAULT_SIZE, pygame.RESIZABLE)
            self._font = pygame.font.Font(None, 24)
            self._small_font = pygame.font.Font(None, 18)
            self._clock = pygame.time.Clock()

            while self._running:
                self._handle_events()
                self._render()
                self._tick()

            return 0
        finally:
            pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)

    def _handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self._running = False
        elif pygame.K_1 <= key <= pygame.K_5:
            self._opponent_count = key - pygame.K_0
        elif key == pygame.K_h:
            self._hand_card_count = max(0, self._hand_card_count - 1)
        elif key == pygame.K_j:
            self._hand_card_count = min(20, self._hand_card_count + 1)
        elif key == pygame.K_r:
            self._row_card_count = max(0, self._row_card_count - 1)
        elif key == pygame.K_f:
            self._row_card_count = min(10, self._row_card_count + 1)
        elif key == pygame.K_d:
            self._show_labels = not self._show_labels

    def _render(self) -> None:
        if self._screen is None:
            raise RuntimeError("LayoutDebugApp not initialized")

        width, height = self._screen.get_size()
        geometry = compute_board_geometry(
            (width, height),
            row_count=4,
            hand_card_count=self._hand_card_count,
            opponent_count=self._opponent_count,
        )

        self._draw_background(geometry.window_rect)
        self._draw_regions(geometry)
        self._draw_row_centers(geometry)
        self._draw_hand_centers(geometry)
        self._draw_opponent_slots(geometry)
        self._draw_help(geometry.window_rect)

        pygame.display.flip()

    def _draw_background(self, window_rect: pygame.Rect) -> None:
        if self._screen is None:
            raise RuntimeError("LayoutDebugApp not initialized")

        image = _scaled_board_image(window_rect.width, window_rect.height)
        if image is None:
            self._screen.fill((20, 90, 40))
            return
        self._screen.blit(image, window_rect.topleft)

    def _draw_regions(self, geometry: BoardGeometry) -> None:
        self._draw_rect(geometry.main_play_rect, COLOR_MAIN, "main_play_rect", width=3)
        self._draw_rect(geometry.row_area_rect, COLOR_ROW_AREA, "row_area_rect", width=3)
        self._draw_rect(geometry.opponent_area_rect, COLOR_OPPONENT_AREA, "opponent_area_rect", width=3)
        self._draw_rect(geometry.stats_rect, COLOR_STATS, "stats_rect", width=3)
        self._draw_rect(geometry.hand_rect, COLOR_HAND, "hand_rect", width=3)
        self._draw_rect(geometry.overlay_rect, COLOR_OVERLAY, "overlay_rect", width=2)

        for index, column in enumerate(geometry.row_columns):
            self._draw_rect(column, COLOR_ROW_COLUMN, f"row_column[{index}]", width=2)

    def _draw_row_centers(self, geometry: BoardGeometry) -> None:
        for row_index, _column in enumerate(geometry.row_columns):
            placements = row_card_placements(
                geometry,
                row_index=row_index,
                card_count=self._row_card_count,
            )
            for card_index, placement in enumerate(placements):
                self._draw_card_placement(
                    placement,
                    COLOR_ROW_CARD,
                    f"r{row_index}:{card_index}",
                    draw_rect=True,
                )

    def _draw_hand_centers(self, geometry: BoardGeometry) -> None:
        placements = hand_card_placements(geometry, card_count=self._hand_card_count)
        for index, placement in enumerate(placements):
            self._draw_card_placement(
                placement,
                COLOR_HAND_CARD,
                f"h{index}",
                draw_rect=True,
            )

    def _draw_opponent_slots(self, geometry: BoardGeometry) -> None:
        if self._screen is None:
            raise RuntimeError("LayoutDebugApp not initialized")

        for index, slot in enumerate(geometry.opponent_slots):
            pygame.draw.circle(self._screen, COLOR_CIRCLE, slot.circle_center, slot.circle_radius, 3)
            self._draw_cross(slot.circle_center, COLOR_CIRCLE, size=8)
            self._draw_card_placement(
                slot.staged_card,
                COLOR_STAGED_CARD,
                f"p{index}",
                draw_rect=True,
            )

            if self._show_labels:
                self._draw_label(
                    f"circle[{index}]",
                    (slot.circle_center[0] + slot.circle_radius + 4, slot.circle_center[1] - 8),
                    COLOR_CIRCLE,
                )

    def _draw_card_placement(
        self,
        placement: CardPlacement,
        color: pygame.Color,
        label: str,
        *,
        draw_rect: bool,
    ) -> None:
        if draw_rect:
            self._draw_rect(placement.rect, color, label, width=2)
        self._draw_cross(placement.center, color, size=9)

    def _draw_rect(self, rect: pygame.Rect, color: pygame.Color, label: str, *, width: int) -> None:
        if self._screen is None:
            raise RuntimeError("LayoutDebugApp not initialized")

        pygame.draw.rect(self._screen, color, rect, width)
        if self._show_labels:
            self._draw_label(label, (rect.left + 4, rect.top + 4), color)

    def _draw_cross(self, center: tuple[int, int], color: pygame.Color, *, size: int) -> None:
        if self._screen is None:
            raise RuntimeError("LayoutDebugApp not initialized")

        x, y = center
        pygame.draw.line(self._screen, color, (x - size, y), (x + size, y), 2)
        pygame.draw.line(self._screen, color, (x, y - size), (x, y + size), 2)

    def _draw_label(self, text: str, position: tuple[int, int], color: pygame.Color) -> None:
        if self._screen is None or self._small_font is None:
            raise RuntimeError("LayoutDebugApp not initialized")

        surface = self._small_font.render(text, True, color)
        bg_rect = surface.get_rect(topleft=position).inflate(6, 4)
        bg = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        bg.fill(COLOR_TEXT_BG)
        self._screen.blit(bg, bg_rect)
        self._screen.blit(surface, position)

    def _draw_help(self, window_rect: pygame.Rect) -> None:
        if self._screen is None or self._font is None:
            raise RuntimeError("LayoutDebugApp not initialized")

        lines = [
            "Layout Debug",
            f"Mitspieler: {self._opponent_count}   Handkarten: {self._hand_card_count}   Karten/Reihe: {self._row_card_count}",
            "1-5 Mitspieler | H/J Hand +/- | R/F Reihe +/- | D Labels | ESC Ende",
        ]

        x = window_rect.left + 16
        y = window_rect.bottom - 78
        width = min(860, window_rect.width - 32)
        bg_rect = pygame.Rect(x - 8, y - 8, width, 72)

        bg = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        bg.fill(COLOR_TEXT_BG)
        self._screen.blit(bg, bg_rect)

        for index, line in enumerate(lines):
            surface = self._font.render(line, True, pygame.Color(255, 255, 255))
            self._screen.blit(surface, (x, y + index * 22))

    def _tick(self) -> None:
        if self._clock is None:
            raise RuntimeError("LayoutDebugApp not initialized")
        self._clock.tick(FPS)


def run() -> int:
    return LayoutDebugApp().run()


def main() -> None:
    raise SystemExit(run())


@lru_cache(maxsize=64)
def _scaled_board_image(width: int, height: int) -> pygame.Surface | None:
    image = _load_board_image()
    if image is None:
        return None
    return pygame.transform.smoothscale(image, (width, height))


@lru_cache(maxsize=1)
def _load_board_image() -> pygame.Surface | None:
    image_path = _project_root() / "images" / "board.png"
    if not image_path.exists():
        return None
    return pygame.image.load(str(image_path)).convert_alpha()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


if __name__ == "__main__":
    main()
