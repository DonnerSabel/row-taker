from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True, slots=True)
class BoardRegionRatios:
    """Relative rectangles for the current board.png.

    All values are relative to the full window:
    x, y, width, height.

    These are intentionally grouped here so the artwork alignment can be
    adjusted without touching rendering or game logic.
    """

    main_play: tuple[float, float, float, float] = (0.018, 0.066, 0.780, 0.784)
    stats: tuple[float, float, float, float] = (0.819, 0.046, 0.155, 0.782)
    hand: tuple[float, float, float, float] = (0.014, 0.904, 0.975, 0.096)


@dataclass(frozen=True, slots=True)
class BoardLayoutTuning:
    """Fine tuning for derived board geometry.

    The ratios below are deliberately named after their visual meaning. That
    makes manual tuning from debug screenshots much easier.
    """

    regions: BoardRegionRatios = BoardRegionRatios()

    # Space between row area and opponent area.
    main_gap_min_px: int = 6
    main_gap_width_ratio: float = 0.006

    # Width of the opponent strip inside the large upper-left play field.
    opponent_area_empty_width_ratio: float = 0.11
    opponent_area_filled_width_ratio: float = 0.19
    opponent_area_min_width_px: int = 128
    opponent_area_max_width_px: int = 190

    # Distance between the four row columns.
    row_column_gap_min_px: int = 5
    row_column_gap_ratio: float = 0.006

    # Row cards inside the four vertical columns.
    row_card_column_width_ratio: float = 0.90
    row_card_column_height_ratio: float = 0.38
    row_card_normal_row_count_width_ratio: float = 0.94
    row_card_many_row_count_width_ratio: float = 0.84
    row_card_min_width_px: int = 112
    row_card_max_width_px: int = 440
    row_first_card_center_y_ratio: float = 0.115
    row_card_overlap_step_ratio: float = 0.36
    row_card_min_step_px: int = 30

    # Hand cards. They may extend below the window; only the upper-left part
    # must remain visible.
    hand_card_visible_height_ratio: float = 2.10
    hand_card_available_space_base: float = 4.9
    hand_card_available_space_per_card: float = 0.66
    hand_card_min_width_px: int = 145
    hand_card_max_width_px: int = 260
    hand_card_spacing_ratio: float = 0.92
    hand_card_min_spacing_px: int = 52

    # The top edge of each hand card is placed relative to hand_rect.height.
    # Increase this value to move hand cards down. Decrease it to move them up.
    hand_card_top_offset_ratio: float = 0.05

    # Staged opponent cards, shown left of the opponent circles.
    staged_card_height_per_player_ratio: float = 0.38
    staged_card_opponent_area_width_ratio: float = 0.36
    staged_card_min_width_px: int = 44
    staged_card_max_width_px: int = 84

    # Opponent circles.
    opponent_circle_height_per_player_ratio: float = 0.38
    opponent_circle_min_diameter_px: int = 30
    opponent_circle_max_diameter_px: int = 58
    opponent_slot_vertical_margin_ratio: float = 0.025
    opponent_slot_horizontal_margin_ratio: float = 0.055
    opponent_slot_min_margin_px: int = 8

    # Status/overlay area inside stats_rect.
    overlay_margin_x_ratio: float = 0.055
    overlay_margin_y_ratio: float = 0.035
    overlay_min_margin_px: int = 8
    overlay_height_ratio: float = 0.155
    overlay_min_height_px: int = 86


DEFAULT_BOARD_LAYOUT = BoardLayoutTuning()


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
    tuning: BoardLayoutTuning = DEFAULT_BOARD_LAYOUT,
) -> BoardGeometry:
    """Compute all scalable board regions."""

    window_rect = pygame.Rect(0, 0, window_size[0], window_size[1])

    main_play_rect = _relative_rect(window_rect, tuning.regions.main_play)
    stats_rect = _relative_rect(window_rect, tuning.regions.stats)
    hand_rect = _relative_rect(window_rect, tuning.regions.hand)

    opponent_area_width = _opponent_area_width(main_play_rect, opponent_count, tuning)
    gap = max(tuning.main_gap_min_px, round(window_rect.width * tuning.main_gap_width_ratio))

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
    row_columns = _row_columns(row_area_rect, rows, tuning)

    row_card_size = _row_card_size(row_columns, rows, tuning)
    hand_card_size = _hand_card_size(hand_rect, hand_card_count, tuning)
    staged_card_size = _staged_card_size(opponent_area_rect, opponent_count, tuning)
    opponent_slots = _opponent_slots(opponent_area_rect, opponent_count, staged_card_size, tuning)

    overlay_rect = _overlay_rect(stats_rect, tuning)

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
    tuning: BoardLayoutTuning = DEFAULT_BOARD_LAYOUT,
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

    _card_width, card_height = geometry.row_card_size
    center_x = column.centerx
    first_center_y = column.top + max(
        card_height // 2,
        round(column.height * tuning.row_first_card_center_y_ratio),
    )

    if count == 1:
        step = 0
    else:
        available_step = (column.bottom - first_center_y - card_height // 2) // max(1, count - 1)
        step = max(
            tuning.row_card_min_step_px,
            min(round(card_height * tuning.row_card_overlap_step_ratio), available_step),
        )

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
    tuning: BoardLayoutTuning = DEFAULT_BOARD_LAYOUT,
) -> tuple[CardPlacement, ...]:
    """Return placements for the player's hand cards.

    The card centers may intentionally be outside the visible window.
    As long as the upper-left card area is visible, all important information
    can still be read.
    """

    count = max(0, card_count)
    if count == 0:
        return ()

    card_width, card_height = geometry.hand_card_size
    spacing = hand_card_spacing(geometry, card_count=count, tuning=tuning)

    total_width = card_width + (count - 1) * spacing
    first_center_x = geometry.hand_rect.centerx - total_width // 2 + card_width // 2

    card_top = geometry.hand_rect.top + round(geometry.hand_rect.height * tuning.hand_card_top_offset_ratio)
    center_y = card_top + card_height // 2

    return tuple(
        CardPlacement(
            center=(first_center_x + index * spacing, center_y),
            size=geometry.hand_card_size,
        )
        for index in range(count)
    )


def hand_card_spacing(
    geometry: BoardGeometry,
    *,
    card_count: int,
    tuning: BoardLayoutTuning = DEFAULT_BOARD_LAYOUT,
) -> int:
    count = max(1, card_count)
    card_width, _card_height = geometry.hand_card_size
    if count == 1:
        return card_width

    exact_spacing = (geometry.hand_rect.width - card_width) // max(1, count - 1)
    return max(
        tuning.hand_card_min_spacing_px,
        min(round(card_width * tuning.hand_card_spacing_ratio), exact_spacing),
    )


def _relative_rect(base: pygame.Rect, ratios: tuple[float, float, float, float]) -> pygame.Rect:
    x, y, width, height = ratios
    return pygame.Rect(
        base.left + round(base.width * x),
        base.top + round(base.height * y),
        round(base.width * width),
        round(base.height * height),
    )


def _row_columns(
    row_area_rect: pygame.Rect,
    row_count: int,
    tuning: BoardLayoutTuning,
) -> tuple[pygame.Rect, ...]:
    gap = max(tuning.row_column_gap_min_px, round(row_area_rect.width * tuning.row_column_gap_ratio))
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


def _opponent_area_width(
    main_play_rect: pygame.Rect,
    opponent_count: int,
    tuning: BoardLayoutTuning,
) -> int:
    if opponent_count <= 0:
        return max(
            tuning.opponent_area_min_width_px,
            round(main_play_rect.width * tuning.opponent_area_empty_width_ratio),
        )

    return max(
        tuning.opponent_area_min_width_px,
        min(
            round(main_play_rect.width * tuning.opponent_area_filled_width_ratio),
            tuning.opponent_area_max_width_px,
        ),
    )


def _row_card_size(
    row_columns: tuple[pygame.Rect, ...],
    row_count: int,
    tuning: BoardLayoutTuning,
) -> tuple[int, int]:
    if not row_columns:
        return (110, 165)

    column = row_columns[0]
    width_by_column = round(column.width * tuning.row_card_column_width_ratio)
    width_by_height = round(column.height * tuning.row_card_column_height_ratio)

    row_count_ratio = (
        tuning.row_card_normal_row_count_width_ratio
        if row_count <= 4
        else tuning.row_card_many_row_count_width_ratio
    )
    width_by_row_count = round(column.width * row_count_ratio)

    width = min(
        tuning.row_card_max_width_px,
        max(
            tuning.row_card_min_width_px,
            min(width_by_column, width_by_height, width_by_row_count),
        ),
    )
    return (width, round(width * 1.5))


def _hand_card_size(
    hand_rect: pygame.Rect,
    hand_card_count: int,
    tuning: BoardLayoutTuning,
) -> tuple[int, int]:
    count = max(1, hand_card_count)

    width_by_visible_height = round(hand_rect.height * tuning.hand_card_visible_height_ratio)
    width_by_available_space = round(
        hand_rect.width
        / max(
            tuning.hand_card_available_space_base,
            count * tuning.hand_card_available_space_per_card,
        )
    )
    width = min(
        tuning.hand_card_max_width_px,
        max(
            tuning.hand_card_min_width_px,
            min(width_by_visible_height, width_by_available_space),
        ),
    )

    return (width, round(width * 1.5))


def _staged_card_size(
    opponent_area_rect: pygame.Rect,
    opponent_count: int,
    tuning: BoardLayoutTuning,
) -> tuple[int, int]:
    count = max(1, opponent_count)

    available_height_per_player = opponent_area_rect.height / count
    width_by_height = round(available_height_per_player * tuning.staged_card_height_per_player_ratio)
    width_by_area = round(opponent_area_rect.width * tuning.staged_card_opponent_area_width_ratio)
    width = min(
        tuning.staged_card_max_width_px,
        max(tuning.staged_card_min_width_px, min(width_by_height, width_by_area)),
    )

    return (width, round(width * 1.5))


def _opponent_slots(
    opponent_area_rect: pygame.Rect,
    opponent_count: int,
    staged_card_size: tuple[int, int],
    tuning: BoardLayoutTuning,
) -> tuple[OpponentSlotGeometry, ...]:
    count = max(0, opponent_count)
    if count == 0:
        return ()

    circle_radius = _opponent_circle_radius(opponent_area_rect, count, tuning)
    staged_width, staged_height = staged_card_size

    vertical_margin = max(
        10,
        circle_radius + 2,
        staged_height // 2 + 2,
        round(opponent_area_rect.height * tuning.opponent_slot_vertical_margin_ratio),
    )
    usable_height = max(1, opponent_area_rect.height - 2 * vertical_margin)

    if count == 1:
        center_ys = [opponent_area_rect.centery]
    else:
        step = usable_height / (count - 1)
        center_ys = [
            round(opponent_area_rect.top + vertical_margin + index * step)
            for index in range(count)
        ]

    horizontal_margin = max(
        tuning.opponent_slot_min_margin_px,
        round(opponent_area_rect.width * tuning.opponent_slot_horizontal_margin_ratio),
    )

    circle_center_x = opponent_area_rect.right - circle_radius - horizontal_margin
    circle_center_x = _clamp(
        circle_center_x,
        opponent_area_rect.left + circle_radius,
        opponent_area_rect.right - circle_radius,
    )

    staged_center_x = circle_center_x - circle_radius - horizontal_margin - staged_width // 2
    staged_center_x = _clamp(
        staged_center_x,
        opponent_area_rect.left + staged_width // 2,
        opponent_area_rect.right - staged_width // 2,
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


def _opponent_circle_radius(
    opponent_area_rect: pygame.Rect,
    opponent_count: int,
    tuning: BoardLayoutTuning,
) -> int:
    count = max(1, opponent_count)
    available_height_per_player = opponent_area_rect.height / count
    diameter = min(
        tuning.opponent_circle_max_diameter_px,
        max(
            tuning.opponent_circle_min_diameter_px,
            round(available_height_per_player * tuning.opponent_circle_height_per_player_ratio),
        ),
    )
    return diameter // 2


def _overlay_rect(stats_rect: pygame.Rect, tuning: BoardLayoutTuning) -> pygame.Rect:
    margin_x = max(
        tuning.overlay_min_margin_px,
        round(stats_rect.width * tuning.overlay_margin_x_ratio),
    )
    margin_y = max(
        tuning.overlay_min_margin_px,
        round(stats_rect.height * tuning.overlay_margin_y_ratio),
    )

    return pygame.Rect(
        stats_rect.left + margin_x,
        stats_rect.top + margin_y,
        max(1, stats_rect.width - 2 * margin_x),
        max(tuning.overlay_min_height_px, round(stats_rect.height * tuning.overlay_height_ratio)),
    )


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))
