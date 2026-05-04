from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True, slots=True)
class CardPlacement:
    """Center-based placement for a card.

    Animation becomes simple with center-based geometry:
    current_center = lerp(start.center, target.center, t)
    current_size = lerp(start.size, target.size, t)
    """

    center: tuple[int, int]
    size: tuple[int, int]

    @property
    def rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, self.size[0], self.size[1])
        rect.center = self.center
        return rect


@dataclass(frozen=True, slots=True)
class OpponentSlotGeometry:
    circle_center: tuple[int, int]
    circle_radius: int
    staged_card: CardPlacement

    @property
    def circle_rect(self) -> pygame.Rect:
        size = self.circle_radius * 2
        rect = pygame.Rect(0, 0, size, size)
        rect.center = self.circle_center
        return rect


@dataclass(frozen=True, slots=True)
class BoardGeometry:
    window_rect: pygame.Rect

    # Three visual regions from the board artwork.
    main_play_rect: pygame.Rect
    row_area_rect: pygame.Rect
    opponent_area_rect: pygame.Rect
    stats_rect: pygame.Rect
    hand_rect: pygame.Rect

    # Derived geometry.
    row_columns: tuple[pygame.Rect, ...]
    opponent_slots: tuple[OpponentSlotGeometry, ...]

    row_card_size: tuple[int, int]
    hand_card_size: tuple[int, int]
    staged_card_size: tuple[int, int]
    overlay_rect: pygame.Rect


def compute_board_geometry(
    window_size: tuple[int, int],
    *,
    row_count: int,
    hand_card_count: int,
    opponent_count: int,
) -> BoardGeometry:
    """Compute all scalable board regions.

    The ratios intentionally follow the student board artwork. They are not
    game rules. They are only presentation geometry and can be tuned here.
    """

    window_rect = pygame.Rect(0, 0, window_size[0], window_size[1])

    # These ratios are based on the current board.png:
    # - big green field in the upper left
    # - narrow opponent strip at the right edge of that field
    # - stats field in the upper right
    # - hand field at the bottom
    main_play_rect = _relative_rect(window_rect, 0.018, 0.080, 0.780, 0.725)
    stats_rect = _relative_rect(window_rect, 0.818, 0.045, 0.164, 0.742)
    hand_rect = _relative_rect(window_rect, 0.014, 0.875, 0.970, 0.110)

    opponent_area_width = _opponent_area_width(main_play_rect, opponent_count)
    gap = max(8, round(window_rect.width * 0.010))

    opponent_area_rect = pygame.Rect(
        main_play_rect.right - opponent_area_width,
        main_play_rect.top,
        opponent_area_width,
        main_play_rect.height,
    )

    row_area_rect = pygame.Rect(
        main_play_rect.left,
        main_play_rect.top,
        main_play_rect.width - opponent_area_width - gap,
        main_play_rect.height,
    )

    rows = max(1, row_count)
    row_columns = _row_columns(row_area_rect, rows)

    row_card_size = _row_card_size(row_columns, rows)
    hand_card_size = _hand_card_size(hand_rect, hand_card_count)
    staged_card_size = _staged_card_size(opponent_area_rect, opponent_count)
    opponent_slots = _opponent_slots(opponent_area_rect, opponent_count, staged_card_size)

    overlay_rect = _relative_rect(window_rect, 0.020, 0.010, 0.520, 0.050)

    return BoardGeometry(
        window_rect=window_rect,
        main_play_rect=main_play_rect,
        row_area_rect=row_area_rect,
        opponent_area_rect=opponent_area_rect,
        stats_rect=stats_rect,
        hand_rect=hand_rect,
        row_columns=row_columns,
        opponent_slots=opponent_slots,
        row_card_size=row_card_size,
        hand_card_size=hand_card_size,
        staged_card_size=staged_card_size,
        overlay_rect=overlay_rect,
    )


def row_card_placements(
    geometry: BoardGeometry,
    *,
    row_index: int,
    card_count: int,
) -> tuple[CardPlacement, ...]:
    """Return target card placements for one row column.

    A row is a vertical column. Cards grow from top to bottom and may overlap.
    """

    if row_index < 0 or row_index >= len(geometry.row_columns):
        return ()

    column = geometry.row_columns[row_index]
    count = max(0, card_count)
    if count == 0:
        return ()

    card_width, card_height = geometry.row_card_size
    center_x = column.centerx
    first_center_y = column.top + max(card_height // 2, round(column.height * 0.12))

    if count == 1:
        step = 0
    else:
        available_step = (column.bottom - first_center_y - card_height // 2) // max(1, count - 1)
        step = max(30, min(round(card_height * 0.38), available_step))

    return tuple(
        CardPlacement(
            center=(center_x, first_center_y + index * step),
            size=geometry.row_card_size,
        )
        for index in range(count)
    )


def hand_card_placements(
    geometry: BoardGeometry,
    *,
    card_count: int,
) -> tuple[CardPlacement, ...]:
    """Return placements for the player's hand cards.

    The card centers may intentionally be outside the visible window.
    For exactly half-visible cards, center_y equals the window bottom.
    """

    count = max(0, card_count)
    if count == 0:
        return ()

    card_width, _card_height = geometry.hand_card_size
    spacing = hand_card_spacing(geometry, card_count=count)

    total_width = card_width + (count - 1) * spacing
    first_center_x = geometry.hand_rect.centerx - total_width // 2 + card_width // 2
    center_y = geometry.window_rect.bottom

    return tuple(
        CardPlacement(
            center=(first_center_x + index * spacing, center_y),
            size=geometry.hand_card_size,
        )
        for index in range(count)
    )


def hand_card_spacing(geometry: BoardGeometry, *, card_count: int) -> int:
    count = max(1, card_count)
    card_width, _card_height = geometry.hand_card_size
    if count == 1:
        return card_width

    exact_spacing = (geometry.hand_rect.width - card_width) // max(1, count - 1)
    return max(46, min(round(card_width * 0.96), exact_spacing))


def _relative_rect(base: pygame.Rect, x: float, y: float, width: float, height: float) -> pygame.Rect:
    return pygame.Rect(
        base.left + round(base.width * x),
        base.top + round(base.height * y),
        round(base.width * width),
        round(base.height * height),
    )


def _row_columns(row_area_rect: pygame.Rect, row_count: int) -> tuple[pygame.Rect, ...]:
    gap = max(8, round(row_area_rect.width * 0.018))
    column_width = max(72, (row_area_rect.width - (row_count - 1) * gap) // row_count)

    return tuple(
        pygame.Rect(
            row_area_rect.left + index * (column_width + gap),
            row_area_rect.top,
            column_width,
            row_area_rect.height,
        )
        for index in range(row_count)
    )


def _opponent_area_width(main_play_rect: pygame.Rect, opponent_count: int) -> int:
    if opponent_count <= 0:
        return max(96, round(main_play_rect.width * 0.11))
    return max(128, min(round(main_play_rect.width * 0.19), 190))


def _row_card_size(row_columns: tuple[pygame.Rect, ...], row_count: int) -> tuple[int, int]:
    if not row_columns:
        return (110, 165)

    column = row_columns[0]
    width_by_column = round(column.width * 0.86)
    width_by_height = round(column.height * 0.38)

    # Four rows are the normal case; still keep this dynamic for future variants.
    width_by_row_count = round(column.width * (0.90 if row_count <= 4 else 0.82))

    width = min(210, max(112, min(width_by_column, width_by_height, width_by_row_count)))
    return (width, round(width * 1.5))


def _hand_card_size(hand_rect: pygame.Rect, hand_card_count: int) -> tuple[int, int]:
    count = max(1, hand_card_count)

    # The hand card is only half visible, so it may be taller than the hand frame.
    width_by_visible_height = round(hand_rect.height * 1.16)
    width_by_available_space = round(hand_rect.width / max(5.8, count * 0.78))
    width = min(205, max(118, min(width_by_visible_height, width_by_available_space)))

    return (width, round(width * 1.5))


def _staged_card_size(opponent_area_rect: pygame.Rect, opponent_count: int) -> tuple[int, int]:
    count = max(1, opponent_count)

    available_height_per_player = opponent_area_rect.height / count
    width_by_height = round(available_height_per_player * 0.42)
    width_by_area = round(opponent_area_rect.width * 0.42)
    width = min(92, max(48, min(width_by_height, width_by_area)))

    return (width, round(width * 1.5))


def _opponent_slots(
    opponent_area_rect: pygame.Rect,
    opponent_count: int,
    staged_card_size: tuple[int, int],
) -> tuple[OpponentSlotGeometry, ...]:
    count = max(0, opponent_count)
    if count == 0:
        return ()

    circle_radius = _opponent_circle_radius(opponent_area_rect, count)
    top_padding = max(12, round(opponent_area_rect.height * 0.035))
    bottom_padding = top_padding
    usable_height = max(circle_radius * 2, opponent_area_rect.height - top_padding - bottom_padding)

    if count == 1:
        center_ys = [opponent_area_rect.centery]
    else:
        step = usable_height / (count - 1)
        center_ys = [
            round(opponent_area_rect.top + top_padding + index * step)
            for index in range(count)
        ]

    circle_center_x = opponent_area_rect.right - circle_radius - max(10, round(opponent_area_rect.width * 0.07))
    staged_width, _staged_height = staged_card_size
    staged_center_x = max(
        opponent_area_rect.left + staged_width // 2,
        circle_center_x - circle_radius - max(8, round(opponent_area_rect.width * 0.06)) - staged_width // 2,
    )

    return tuple(
        OpponentSlotGeometry(
            circle_center=(circle_center_x, center_y),
            circle_radius=circle_radius,
            staged_card=CardPlacement(
                center=(staged_center_x, center_y),
                size=staged_card_size,
            ),
        )
        for center_y in center_ys
    )


def _opponent_circle_radius(opponent_area_rect: pygame.Rect, opponent_count: int) -> int:
    count = max(1, opponent_count)
    available_height_per_player = opponent_area_rect.height / count
    diameter = min(58, max(30, round(available_height_per_player * 0.38)))
    return diameter // 2
