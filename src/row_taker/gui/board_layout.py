from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True, slots=True)
class BoardLayoutTuning:
    """Fine tuning for derived board geometry.

    The ratios below are deliberately named after their visual meaning. That
    makes manual tuning from debug screenshots much easier.
    """

    # Rows occupy the upper part of the play area. The margins are independent
    # of any background artwork and leave a clear gap above the hand cards.
    row_area_horizontal_margin_min_px: int = 6
    row_area_horizontal_margin_width_ratio: float = 0.008
    row_area_top_margin_min_px: int = 28
    row_area_top_margin_height_ratio: float = 0.050
    row_hand_gap_min_px: int = 22
    row_hand_gap_height_ratio: float = 0.030

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

    # Artwork-independent split between play area and sidebar.
    content_margin_min_px: int = 12
    content_margin_short_side_ratio: float = 0.018
    sidebar_gap_min_px: int = 10
    sidebar_gap_width_ratio: float = 0.010
    sidebar_width_ratio: float = 0.34
    sidebar_min_width_px: int = 300
    sidebar_max_width_px: int = 520
    play_area_min_width_px: int = 460

    # The hand occupies a shallow strip at the bottom of the new play area.
    # Cards may still extend below the window, but they must never extend into
    # the sidebar horizontally.
    play_hand_height_ratio: float = 0.095
    play_hand_min_height_px: int = 64
    play_hand_max_height_px: int = 90

    sidebar_inner_margin_min_px: int = 10
    sidebar_inner_margin_ratio: float = 0.025
    sidebar_section_gap_min_px: int = 8
    sidebar_section_gap_height_ratio: float = 0.012
    sidebar_header_height_ratio: float = 0.08
    sidebar_header_min_height_px: int = 48
    sidebar_header_max_height_px: int = 70
    sidebar_own_player_height_ratio: float = 0.20
    sidebar_own_player_min_height_px: int = 116
    sidebar_own_player_max_height_px: int = 160

    player_tile_inner_margin_px: int = 6
    player_tile_preferred_height_px: int = 72
    player_tile_card_left_offset_px: int = 6
    player_tile_card_top_offset_px: int = 6
    player_tile_card_width_ratio: float = 0.18
    player_tile_card_min_width_px: int = 64
    player_tile_card_max_width_px: int = 86
    player_tile_card_info_gap_px: int = 10
    player_tile_info_vertical_margin_px: int = 3


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
class PlayerTileGeometry:
    """Prepared geometry for one player tile in the new sidebar.

    ``tile_rect`` and ``info_rect`` never overlap another player's text area.
    Every opponent tile in one layout has the same height. The card uses a
    fixed top-left offset from its tile and may intentionally extend beyond
    ``tile_rect`` so neighbouring cards can overlap vertically.
    """

    tile_rect: pygame.Rect
    info_rect: pygame.Rect
    card_placement: CardPlacement


@dataclass(frozen=True, slots=True)
class BoardGeometry:
    window_rect: pygame.Rect
    play_area_rect: pygame.Rect
    row_area_rect: pygame.Rect
    hand_rect: pygame.Rect

    sidebar_rect: pygame.Rect
    sidebar_header_rect: pygame.Rect
    opponent_list_rect: pygame.Rect
    own_player_rect: pygame.Rect
    opponent_tiles: tuple[PlayerTileGeometry, ...]
    own_player_tile: PlayerTileGeometry

    row_columns: tuple[pygame.Rect, ...]
    row_card_size: tuple[int, int]
    hand_card_size: tuple[int, int]


def compute_board_geometry(
    window_size: tuple[int, int],
    *,
    row_count: int,
    hand_card_count: int,
    opponent_count: int,
    tuning: BoardLayoutTuning = DEFAULT_BOARD_LAYOUT,
) -> BoardGeometry:
    """Compute the complete artwork-independent game-screen geometry."""

    window_rect = pygame.Rect(0, 0, window_size[0], window_size[1])
    (
        play_area_rect,
        sidebar_rect,
        sidebar_header_rect,
        opponent_list_rect,
        own_player_rect,
    ) = _game_screen_regions(window_rect, tuning)

    hand_rect = _play_area_hand_rect(play_area_rect, tuning)
    row_area_rect = _play_area_row_rect(play_area_rect, hand_rect, tuning)
    rows = max(1, row_count)
    row_columns = _row_columns(row_area_rect, rows, tuning)

    player_card_size = _player_tile_card_size(sidebar_rect, tuning)
    opponent_tiles = _opponent_tiles(
        opponent_list_rect,
        opponent_count,
        player_card_size,
        tuning,
    )
    own_player_tile = _own_player_tile(
        own_player_rect,
        player_card_size,
        tuning,
    )

    return BoardGeometry(
        window_rect=window_rect,
        play_area_rect=play_area_rect,
        row_area_rect=row_area_rect,
        hand_rect=hand_rect,
        sidebar_rect=sidebar_rect,
        sidebar_header_rect=sidebar_header_rect,
        opponent_list_rect=opponent_list_rect,
        own_player_rect=own_player_rect,
        opponent_tiles=opponent_tiles,
        own_player_tile=own_player_tile,
        row_columns=row_columns,
        row_card_size=_row_card_size(row_columns, rows, tuning),
        hand_card_size=_hand_card_size(hand_rect, hand_card_count, tuning),
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

    card_top = geometry.hand_rect.top + round(
        geometry.hand_rect.height * tuning.hand_card_top_offset_ratio
    )
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
    preferred_spacing = max(
        tuning.hand_card_min_spacing_px,
        round(card_width * tuning.hand_card_spacing_ratio),
    )
    return max(1, min(preferred_spacing, exact_spacing))


def _game_screen_regions(
    window_rect: pygame.Rect,
    tuning: BoardLayoutTuning,
) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
    """Return the play/sidebar split and the prepared sidebar sections."""

    content_margin = max(
        tuning.content_margin_min_px,
        round(min(window_rect.size) * tuning.content_margin_short_side_ratio),
    )
    sidebar_gap = max(
        tuning.sidebar_gap_min_px,
        round(window_rect.width * tuning.sidebar_gap_width_ratio),
    )

    available_width = max(1, window_rect.width - 2 * content_margin)
    desired_sidebar_width = _clamp(
        round(window_rect.width * tuning.sidebar_width_ratio),
        tuning.sidebar_min_width_px,
        tuning.sidebar_max_width_px,
    )
    maximum_sidebar_width = max(
        1,
        available_width - sidebar_gap - tuning.play_area_min_width_px,
    )
    sidebar_width = min(desired_sidebar_width, maximum_sidebar_width)
    play_width = max(1, available_width - sidebar_gap - sidebar_width)
    content_height = max(1, window_rect.height - 2 * content_margin)

    play_area_rect = pygame.Rect(
        window_rect.left + content_margin,
        window_rect.top + content_margin,
        play_width,
        content_height,
    )
    sidebar_rect = pygame.Rect(
        play_area_rect.right + sidebar_gap,
        play_area_rect.top,
        sidebar_width,
        content_height,
    )

    inner_margin = max(
        tuning.sidebar_inner_margin_min_px,
        round(sidebar_rect.width * tuning.sidebar_inner_margin_ratio),
    )
    section_gap = max(
        tuning.sidebar_section_gap_min_px,
        round(sidebar_rect.height * tuning.sidebar_section_gap_height_ratio),
    )
    inner_rect = sidebar_rect.inflate(-2 * inner_margin, -2 * inner_margin)

    header_height = _clamp(
        round(sidebar_rect.height * tuning.sidebar_header_height_ratio),
        tuning.sidebar_header_min_height_px,
        tuning.sidebar_header_max_height_px,
    )
    own_player_height = _clamp(
        round(sidebar_rect.height * tuning.sidebar_own_player_height_ratio),
        tuning.sidebar_own_player_min_height_px,
        tuning.sidebar_own_player_max_height_px,
    )

    fixed_height = header_height + own_player_height + 2 * section_gap
    opponent_height = max(1, inner_rect.height - fixed_height)

    sidebar_header_rect = pygame.Rect(
        inner_rect.left,
        inner_rect.top,
        inner_rect.width,
        header_height,
    )
    opponent_list_rect = pygame.Rect(
        inner_rect.left,
        sidebar_header_rect.bottom + section_gap,
        inner_rect.width,
        opponent_height,
    )
    own_player_rect = pygame.Rect(
        inner_rect.left,
        opponent_list_rect.bottom + section_gap,
        inner_rect.width,
        own_player_height,
    )

    return (
        play_area_rect,
        sidebar_rect,
        sidebar_header_rect,
        opponent_list_rect,
        own_player_rect,
    )


def _play_area_hand_rect(
    play_area_rect: pygame.Rect,
    tuning: BoardLayoutTuning,
) -> pygame.Rect:
    """Return the hand strip constrained to the artwork-independent play area."""

    hand_height = _clamp(
        round(play_area_rect.height * tuning.play_hand_height_ratio),
        tuning.play_hand_min_height_px,
        tuning.play_hand_max_height_px,
    )
    return pygame.Rect(
        play_area_rect.left,
        play_area_rect.bottom - hand_height,
        play_area_rect.width,
        hand_height,
    )


def _play_area_row_rect(
    play_area_rect: pygame.Rect,
    hand_rect: pygame.Rect,
    tuning: BoardLayoutTuning,
) -> pygame.Rect:
    """Return the row area above the hand, entirely inside the play area."""

    horizontal_margin = max(
        tuning.row_area_horizontal_margin_min_px,
        round(play_area_rect.width * tuning.row_area_horizontal_margin_width_ratio),
    )
    top_margin = max(
        tuning.row_area_top_margin_min_px,
        round(play_area_rect.height * tuning.row_area_top_margin_height_ratio),
    )
    hand_gap = max(
        tuning.row_hand_gap_min_px,
        round(play_area_rect.height * tuning.row_hand_gap_height_ratio),
    )
    left = play_area_rect.left + horizontal_margin
    right = play_area_rect.right - horizontal_margin
    top = play_area_rect.top + top_margin
    bottom = hand_rect.top - hand_gap
    return pygame.Rect(
        left,
        top,
        max(1, right - left),
        max(1, bottom - top),
    )


def _player_tile_card_size(
    sidebar_rect: pygame.Rect,
    tuning: BoardLayoutTuning,
) -> tuple[int, int]:
    width = _clamp(
        round(sidebar_rect.width * tuning.player_tile_card_width_ratio),
        tuning.player_tile_card_min_width_px,
        tuning.player_tile_card_max_width_px,
    )
    return (width, round(width * 1.5))


def _opponent_tiles(
    opponent_list_rect: pygame.Rect,
    opponent_count: int,
    card_size: tuple[int, int],
    tuning: BoardLayoutTuning,
) -> tuple[PlayerTileGeometry, ...]:
    count = max(0, opponent_count)
    if count == 0:
        return ()

    card_width, card_height = card_size
    card_left = opponent_list_rect.left + tuning.player_tile_card_left_offset_px
    info_left = card_left + card_width + tuning.player_tile_card_info_gap_px
    info_width = max(
        1,
        opponent_list_rect.right - tuning.player_tile_inner_margin_px - info_left,
    )

    tile_height = _opponent_tile_height(
        opponent_list_rect,
        opponent_count=count,
        card_height=card_height,
        tuning=tuning,
    )

    tiles: list[PlayerTileGeometry] = []
    for index in range(count):
        tile_rect = pygame.Rect(
            opponent_list_rect.left,
            opponent_list_rect.top + index * tile_height,
            opponent_list_rect.width,
            tile_height,
        )
        info_rect = pygame.Rect(
            info_left,
            tile_rect.top + tuning.player_tile_info_vertical_margin_px,
            info_width,
            max(
                1,
                tile_rect.height - 2 * tuning.player_tile_info_vertical_margin_px,
            ),
        )
        card_top = tile_rect.top + tuning.player_tile_card_top_offset_px
        tiles.append(
            PlayerTileGeometry(
                tile_rect=tile_rect,
                info_rect=info_rect,
                card_placement=CardPlacement(
                    center=(
                        card_left + card_width // 2,
                        card_top + card_height // 2,
                    ),
                    size=card_size,
                ),
            )
        )

    return tuple(tiles)


def _opponent_tile_height(
    opponent_list_rect: pygame.Rect,
    *,
    opponent_count: int,
    card_height: int,
    tuning: BoardLayoutTuning,
) -> int:
    """Return one shared tile height while keeping the last card in bounds."""

    count = max(1, opponent_count)
    maximum_by_tiles = max(1, opponent_list_rect.height // count)
    if count == 1:
        maximum_by_cards = maximum_by_tiles
    else:
        remaining_height = (
            opponent_list_rect.height - tuning.player_tile_card_top_offset_px - card_height
        )
        maximum_by_cards = max(1, remaining_height // (count - 1))

    return max(
        1,
        min(
            tuning.player_tile_preferred_height_px,
            maximum_by_tiles,
            maximum_by_cards,
        ),
    )


def _own_player_tile(
    own_player_rect: pygame.Rect,
    card_size: tuple[int, int],
    tuning: BoardLayoutTuning,
) -> PlayerTileGeometry:
    card_width, card_height = card_size
    card_left = own_player_rect.left + tuning.player_tile_card_left_offset_px
    card_top = own_player_rect.top + tuning.player_tile_card_top_offset_px
    info_left = card_left + card_width + tuning.player_tile_card_info_gap_px
    info_rect = pygame.Rect(
        info_left,
        own_player_rect.top + tuning.player_tile_inner_margin_px,
        max(
            1,
            own_player_rect.right - tuning.player_tile_inner_margin_px - info_left,
        ),
        max(
            1,
            own_player_rect.height - 2 * tuning.player_tile_inner_margin_px,
        ),
    )

    return PlayerTileGeometry(
        tile_rect=own_player_rect.copy(),
        info_rect=info_rect,
        card_placement=CardPlacement(
            center=(
                card_left + card_width // 2,
                card_top + card_height // 2,
            ),
            size=card_size,
        ),
    )


def _row_columns(
    row_area_rect: pygame.Rect,
    row_count: int,
    tuning: BoardLayoutTuning,
) -> tuple[pygame.Rect, ...]:
    gap = max(
        tuning.row_column_gap_min_px, round(row_area_rect.width * tuning.row_column_gap_ratio)
    )
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


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))
