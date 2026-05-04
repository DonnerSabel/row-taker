from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pygame

from row_taker.client.actions import (
    ClientActionAdvancePresentation,
    ClientActionChooseCard,
    ClientActionChooseRow,
)
from row_taker.client.state import ClientState
from row_taker.engine.game import Phase
from row_taker.engine.game.models import PlayerID
from row_taker.gui_demo.layout import DemoLayout
from row_taker.gui_demo.primitives import (
    ACCENT,
    CARD_FILL,
    CARD_SELECTED,
    PANEL_BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    PrimitiveDrawer,
)
from row_taker.gui_demo.ui.common_render import format_presentation_event
from row_taker.gui_demo.ui.screen_result import NO_SCREEN_RESULT, ScreenResult


@dataclass(frozen=True, slots=True)
class CardTarget:
    card_value: int
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class RowTarget:
    row_id: object
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class ContinueTarget:
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class GameScreenTargets:
    card_targets: tuple[CardTarget, ...] = ()
    row_targets: tuple[RowTarget, ...] = ()
    continue_target: ContinueTarget | None = None


@dataclass(frozen=True, slots=True)
class OpponentSlot:
    player_id: PlayerID
    player_name: str
    circle_rect: pygame.Rect
    staged_card_rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class BoardLayout:
    window_rect: pygame.Rect

    # The actual large board field in the upper left.
    main_play_rect: pygame.Rect

    # Left part of main_play_rect: four vertical row columns.
    row_columns_rect: pygame.Rect
    row_rects: tuple[pygame.Rect, ...]

    # Right part of main_play_rect: opponent circles and played-card staging area.
    opponent_slots_rect: pygame.Rect
    opponent_slots: tuple[OpponentSlot, ...]

    # Small upper right field.
    stats_rect: pygame.Rect

    # Bottom hand area.
    hand_rect: pygame.Rect

    overlay_rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class GameScreen:
    state: ClientState
    frame_count: int
    last_action_summary: str

    def build_targets(self, layout: DemoLayout) -> GameScreenTargets:
        board_layout = _board_layout(layout.window_rect, self.state)
        return build_game_screen_targets(board_layout, self.state)

    def handle_event(
        self,
        event: pygame.event.Event,
        targets: GameScreenTargets | None,
    ) -> ScreenResult:
        return handle_game_event(event, state=self.state, game_targets=targets)

    def render(
        self,
        screen: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
        layout: DemoLayout,
        targets: GameScreenTargets,
    ) -> None:
        board_layout = _board_layout(layout.window_rect, self.state)
        render_game_screen(
            screen,
            drawer=drawer,
            board_layout=board_layout,
            client_state=self.state,
            game_targets=targets,
            last_action_summary=self.last_action_summary,
        )


def build_game_screen_targets(board_layout: BoardLayout, state: ClientState) -> GameScreenTargets:
    return GameScreenTargets(
        card_targets=_build_card_targets(board_layout, state),
        row_targets=_build_row_targets(board_layout, state),
        continue_target=_build_continue_target(board_layout, state),
    )


def handle_game_event(
    event: pygame.event.Event,
    *,
    state: ClientState | None,
    game_targets: GameScreenTargets | None,
) -> ScreenResult:
    if event.type == pygame.QUIT:
        return ScreenResult(request_quit=True)

    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return ScreenResult(request_quit=True)

    if state is None or game_targets is None:
        return NO_SCREEN_RESULT

    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and state.pending_presentation_events:
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_left_click(event.pos, game_targets=game_targets)

    return NO_SCREEN_RESULT


def render_game_screen(
    screen: pygame.Surface,
    *,
    drawer: PrimitiveDrawer,
    board_layout: BoardLayout,
    client_state: ClientState,
    game_targets: GameScreenTargets,
    last_action_summary: str,
) -> None:
    _draw_full_background(screen, board_layout.window_rect)
    _draw_rows(screen, drawer, board_layout, client_state, game_targets)
    _draw_opponent_slots(screen, drawer, board_layout, client_state)
    _draw_hand(screen, drawer, client_state, game_targets)
    _draw_stats_field(screen, drawer, board_layout, client_state)
    _draw_status_overlay(screen, drawer, board_layout, client_state, last_action_summary, game_targets)


def _handle_left_click(position: tuple[int, int], *, game_targets: GameScreenTargets) -> ScreenResult:
    # Hand cards overlap. Check front-to-back.
    for target in reversed(game_targets.card_targets):
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseCard(card_value=target.card_value))

    for target in game_targets.row_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseRow(row_id=target.row_id))

    if game_targets.continue_target is not None and game_targets.continue_target.rect.collidepoint(position):
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    return NO_SCREEN_RESULT


def _board_layout(window_rect: pygame.Rect, state: ClientState) -> BoardLayout:
    public_state = state.public_state
    row_count = len(public_state.rows) if public_state is not None else 4

    # Coordinates are relative to the board.png design:
    # - large field: upper left
    # - stats field: upper right
    # - hand field: bottom
    padding_x = max(18, round(window_rect.width * 0.018))
    top_ui_height = max(52, round(window_rect.height * 0.075))
    gap = max(14, round(window_rect.width * 0.012))
    bottom_hand_height = max(118, round(window_rect.height * 0.22))
    bottom_margin = max(10, round(window_rect.height * 0.018))

    stats_width = max(150, round(window_rect.width * 0.16))
    stats_rect = pygame.Rect(
        window_rect.right - padding_x - stats_width,
        top_ui_height,
        stats_width,
        window_rect.height - top_ui_height - bottom_hand_height - bottom_margin - gap,
    )

    main_play_rect = pygame.Rect(
        padding_x,
        top_ui_height,
        stats_rect.left - padding_x - gap,
        stats_rect.height,
    )

    opponent_width = _opponent_area_width(main_play_rect, state)
    opponent_slots_rect = pygame.Rect(
        main_play_rect.right - opponent_width,
        main_play_rect.top,
        opponent_width,
        main_play_rect.height,
    )

    row_columns_rect = pygame.Rect(
        main_play_rect.left,
        main_play_rect.top,
        main_play_rect.width - opponent_width - gap,
        main_play_rect.height,
    )

    row_rects = _build_row_column_rects(row_columns_rect, max(1, row_count))

    hand_rect = pygame.Rect(
        padding_x,
        window_rect.height - bottom_hand_height,
        window_rect.width - 2 * padding_x,
        bottom_hand_height - bottom_margin,
    )

    overlay_rect = pygame.Rect(
        padding_x,
        8,
        min(680, window_rect.width - 2 * padding_x),
        max(38, top_ui_height - 14),
    )

    opponent_slots = _build_opponent_slots(opponent_slots_rect, state)

    return BoardLayout(
        window_rect=window_rect,
        main_play_rect=main_play_rect,
        row_columns_rect=row_columns_rect,
        row_rects=row_rects,
        opponent_slots_rect=opponent_slots_rect,
        opponent_slots=opponent_slots,
        stats_rect=stats_rect,
        hand_rect=hand_rect,
        overlay_rect=overlay_rect,
    )


def _build_row_column_rects(row_columns_rect: pygame.Rect, row_count: int) -> tuple[pygame.Rect, ...]:
    column_gap = max(8, round(row_columns_rect.width * 0.018))
    column_width = max(72, (row_columns_rect.width - (row_count - 1) * column_gap) // row_count)

    return tuple(
        pygame.Rect(
            row_columns_rect.left + index * (column_width + column_gap),
            row_columns_rect.top,
            column_width,
            row_columns_rect.height,
        )
        for index in range(row_count)
    )


def _opponent_area_width(main_play_rect: pygame.Rect, state: ClientState) -> int:
    opponent_count = len(_opponent_players(state))
    if opponent_count == 0:
        return max(96, round(main_play_rect.width * 0.11))

    # Up to five opponents: enough space for a staged card plus one circle.
    return max(128, min(round(main_play_rect.width * 0.19), 190))


def _build_opponent_slots(rect: pygame.Rect, state: ClientState) -> tuple[OpponentSlot, ...]:
    opponents = _opponent_players(state)
    if not opponents:
        return ()

    count = len(opponents)
    circle_size = _opponent_circle_size(rect, count)
    staged_width, staged_height = _staged_card_size(rect, count)
    top_padding = max(12, round(rect.height * 0.035))
    bottom_padding = top_padding
    usable_height = max(circle_size, rect.height - top_padding - bottom_padding)

    if count == 1:
        center_ys = [rect.top + rect.height // 2]
    else:
        step = usable_height / (count - 1)
        center_ys = [round(rect.top + top_padding + index * step) for index in range(count)]

    circle_x = rect.right - circle_size - max(10, round(rect.width * 0.07))
    staged_x = max(rect.left, circle_x - staged_width - max(8, round(rect.width * 0.06)))

    slots: list[OpponentSlot] = []
    for player, center_y in zip(opponents, center_ys, strict=False):
        circle_rect = pygame.Rect(circle_x, center_y - circle_size // 2, circle_size, circle_size)
        staged_card_rect = pygame.Rect(staged_x, center_y - staged_height // 2, staged_width, staged_height)
        slots.append(
            OpponentSlot(
                player_id=player.player_id,
                player_name=player.name,
                circle_rect=circle_rect,
                staged_card_rect=staged_card_rect,
            )
        )

    return tuple(slots)


def _opponent_players(state: ClientState) -> tuple[Any, ...]:
    public_state = state.public_state
    if public_state is None:
        return ()

    return tuple(player for player in public_state.players if player.player_id != state.own_player_id)


def _build_card_targets(board_layout: BoardLayout, state: ClientState) -> tuple[CardTarget, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()

    card_count = len(player_state.hand)
    if card_count == 0:
        return ()

    card_width, card_height = _hand_card_size(board_layout.hand_rect, card_count)
    spacing = _hand_spacing(board_layout.hand_rect, card_width, card_count)

    x_start = board_layout.hand_rect.centerx - ((card_count - 1) * spacing + card_width) // 2
    x_start = max(board_layout.hand_rect.left, x_start)

    # Only the upper half is visible.
    visible_y = board_layout.window_rect.height - card_height // 2

    targets: list[CardTarget] = []
    for index, card in enumerate(player_state.hand):
        rect = pygame.Rect(
            x_start + index * spacing,
            visible_y,
            card_width,
            card_height,
        )
        targets.append(CardTarget(card_value=card.value, rect=rect))

    return tuple(targets)


def _build_row_targets(board_layout: BoardLayout, state: ClientState) -> tuple[RowTarget, ...]:
    public_state = state.public_state
    player_state = state.player_state
    if public_state is None or player_state is None:
        return ()

    if player_state.phase_info.phase != Phase.CHOOSE_ROW:
        return ()

    selectable = set(player_state.get_selectable_row_ids_for_choose_row())
    targets: list[RowTarget] = []
    for row, rect in zip(public_state.rows, board_layout.row_rects, strict=False):
        if row.row_id in selectable:
            targets.append(RowTarget(row_id=row.row_id, rect=rect))
    return tuple(targets)


def _build_continue_target(board_layout: BoardLayout, state: ClientState) -> ContinueTarget | None:
    if not state.pending_presentation_events:
        return None

    rect = pygame.Rect(
        board_layout.stats_rect.left + 12,
        board_layout.stats_rect.bottom - 46,
        max(1, board_layout.stats_rect.width - 24),
        34,
    )
    return ContinueTarget(rect=rect)


def _draw_full_background(screen: pygame.Surface, window_rect: pygame.Rect) -> None:
    board = _scaled_board_image_full(window_rect.width, window_rect.height)
    if board is None:
        screen.fill((18, 84, 38))
        return

    # board.png is the full background. No cropping, aspect ratio ignored.
    screen.blit(board, window_rect.topleft)


def _draw_rows(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    board_layout: BoardLayout,
    client_state: ClientState,
    game_targets: GameScreenTargets,
) -> None:
    public_state = client_state.public_state
    if public_state is None:
        return

    row_target_by_id = {target.row_id: target for target in game_targets.row_targets}

    for row, row_rect in zip(public_state.rows, board_layout.row_rects, strict=False):
        selectable = row.row_id in row_target_by_id
        _draw_row_column(screen, drawer, row_rect, row_id=row.row_id, cards=row.cards, selectable=selectable)


def _draw_row_column(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    row_id: object,
    cards: tuple[Any, ...],
    selectable: bool,
) -> None:
    # Light debug tint only; the board artwork remains dominant.
    lane_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(lane_surface, pygame.Color(0, 0, 0, 22), lane_surface.get_rect(), border_radius=8)
    screen.blit(lane_surface, rect)

    border = ACCENT if selectable else pygame.Color(255, 255, 255, 28)
    pygame.draw.rect(screen, border, rect, 3 if selectable else 1, border_radius=8)

    drawer.draw_text(
        screen,
        str(row_id),
        (rect.left + 8, rect.top + 6),
        role="small",
        color=ACCENT if selectable else TEXT_MUTED,
    )

    if not cards:
        return

    card_width, card_height = _row_card_size(rect, len(cards))
    x = rect.centerx - card_width // 2
    y = rect.top + max(28, round(rect.height * 0.055))
    visible_step = _row_visible_step(rect, card_height, len(cards))

    for index, card in enumerate(cards):
        card_rect = pygame.Rect(
            x,
            y + index * visible_step,
            card_width,
            card_height,
        )
        _draw_card_image_or_fallback(screen, drawer, card_rect, card, selected=selectable)


def _draw_opponent_slots(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    board_layout: BoardLayout,
    client_state: ClientState,
) -> None:
    revealed_by_player = _revealed_card_values_by_player(client_state)

    for index, slot in enumerate(board_layout.opponent_slots):
        color = _player_color(index)
        pygame.draw.ellipse(screen, color, slot.circle_rect)
        pygame.draw.ellipse(screen, pygame.Color(255, 255, 255, 150), slot.circle_rect, 2)

        initials = _initials(slot.player_name)
        text_pos = (
            slot.circle_rect.centerx - 8,
            slot.circle_rect.centery - 8,
        )
        drawer.draw_text(screen, initials, text_pos, role="tiny", color=TEXT_PRIMARY)

        card_value = revealed_by_player.get(slot.player_id)
        if card_value is None:
            _draw_staged_card_back(screen, slot.staged_card_rect)
        else:
            _draw_card_value_image_or_back(screen, drawer, slot.staged_card_rect, card_value)


def _draw_staged_card_back(screen: pygame.Surface, rect: pygame.Rect) -> None:
    back = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(back, pygame.Color(18, 28, 40, 130), back.get_rect(), border_radius=6)
    screen.blit(back, rect)
    pygame.draw.rect(screen, pygame.Color(255, 255, 255, 65), rect, 1, border_radius=6)


def _draw_card_value_image_or_back(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    card_value: int,
) -> None:
    image = _scaled_card_image(card_value, rect.width, rect.height)
    if image is None:
        pygame.draw.rect(screen, CARD_FILL, rect, border_radius=6)
        pygame.draw.rect(screen, PANEL_BORDER, rect, 1, border_radius=6)
        drawer.draw_text(screen, str(card_value), (rect.left + 6, rect.top + 4), role="small")
        return

    screen.blit(image, rect)


def _revealed_card_values_by_player(client_state: ClientState) -> dict[PlayerID, int]:
    revealed = client_state.revealed_trick
    if revealed is None:
        return {}
    return {play.player_id: play.card_value for play in revealed.plays}


def _draw_hand(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    client_state: ClientState,
    game_targets: GameScreenTargets,
) -> None:
    player_state = client_state.player_state
    if player_state is None:
        return

    target_by_value = {target.card_value: target for target in game_targets.card_targets}
    for card in player_state.hand:
        target = target_by_value.get(card.value)
        if target is None:
            continue
        _draw_card_image_or_fallback(screen, drawer, target.rect, card)

    if player_state.phase_info.phase == Phase.CHOOSE_ROW and player_state.pending_card_value() is not None:
        pending_rect = pygame.Rect(24, max(60, game_targets.card_targets[0].rect.top - 42), 270, 34)
        _draw_overlay_box(screen, pending_rect)
        drawer.draw_text(
            screen,
            f"Reihe für Karte {player_state.pending_card_value()} wählen",
            (pending_rect.left + 10, pending_rect.top + 8),
            role="small",
            color=ACCENT,
        )


def _draw_stats_field(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    board_layout: BoardLayout,
    client_state: ClientState,
) -> None:
    rect = board_layout.stats_rect
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(overlay, pygame.Color(0, 0, 0, 35), overlay.get_rect(), border_radius=12)
    screen.blit(overlay, rect)

    player_state = client_state.player_state
    public_state = client_state.public_state
    own_score = "-"
    own_name = "-"
    if player_state is not None:
        own_player = player_state.self_player()
        own_score = str(own_player.score)
        own_name = own_player.name

    drawer.draw_text(screen, own_name, (rect.left + 12, rect.top + 14), role="small", color=TEXT_MUTED)
    drawer.draw_text(screen, "Hornochsen", (rect.left + 12, rect.top + 42), role="small", color=TEXT_MUTED)
    drawer.draw_text(screen, own_score, (rect.left + 12, rect.top + 66), role="title", color=ACCENT)

    if public_state is not None:
        y = rect.top + 112
        for player in public_state.players:
            marker = "★ " if player.player_id == client_state.own_player_id else ""
            drawer.draw_text(
                screen,
                f"{marker}{player.name}: {player.score}",
                (rect.left + 12, y),
                role="tiny",
                color=TEXT_PRIMARY if marker else TEXT_MUTED,
            )
            y += 20
            if y > rect.bottom - 54:
                break


def _draw_status_overlay(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    board_layout: BoardLayout,
    client_state: ClientState,
    last_action_summary: str,
    game_targets: GameScreenTargets,
) -> None:
    _draw_overlay_box(screen, board_layout.overlay_rect)

    player_state = client_state.player_state
    phase = player_state.phase_info.phase.value if player_state is not None else "-"
    player_name = player_state.self_player_name() if player_state is not None else "-"

    line_1 = f"{player_name}  |  Phase: {phase}  |  Aktion: {client_state.pending_action.value}"
    drawer.draw_text(
        screen,
        line_1,
        (board_layout.overlay_rect.left + 10, board_layout.overlay_rect.top + 8),
        role="small",
    )

    line_2 = client_state.flash_message.text if client_state.flash_message is not None else last_action_summary
    drawer.draw_text(
        screen,
        line_2,
        (board_layout.overlay_rect.left + 10, board_layout.overlay_rect.top + 30),
        role="tiny",
        color=TEXT_MUTED,
    )

    if client_state.pending_presentation_events:
        events_rect = pygame.Rect(
            board_layout.stats_rect.left,
            board_layout.stats_rect.bottom - 142,
            board_layout.stats_rect.width,
            96,
        )
        _draw_overlay_box(screen, events_rect)
        lines = [format_presentation_event(event) for event in client_state.pending_presentation_events[:3]]
        drawer.draw_wrapped_lines(
            screen,
            lines,
            events_rect.inflate(-18, -18),
            role="tiny",
            color=TEXT_PRIMARY,
        )

    if game_targets.continue_target is not None:
        _draw_overlay_box(screen, game_targets.continue_target.rect)
        drawer.draw_text(
            screen,
            "Weiter [Leertaste]",
            (game_targets.continue_target.rect.left + 10, game_targets.continue_target.rect.top + 8),
            role="small",
            color=ACCENT,
        )


def _draw_overlay_box(screen: pygame.Surface, rect: pygame.Rect) -> None:
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(overlay, pygame.Color(0, 0, 0, 120), overlay.get_rect(), border_radius=8)
    screen.blit(overlay, rect)
    pygame.draw.rect(screen, pygame.Color(255, 255, 255, 45), rect, 1, border_radius=8)


def _draw_card_image_or_fallback(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    card: Any,
    *,
    selected: bool = False,
) -> None:
    image = _scaled_card_image(card.value, rect.width, rect.height)
    if image is None:
        pygame.draw.rect(screen, CARD_SELECTED if selected else CARD_FILL, rect, border_radius=6)
        pygame.draw.rect(screen, ACCENT if selected else PANEL_BORDER, rect, 2 if selected else 1, border_radius=6)
        drawer.draw_text(screen, str(card.value), (rect.left + 8, rect.top + 6), role="body")
        drawer.draw_text(screen, f"{card.bullheads} bh", (rect.left + 8, rect.top + 30), role="small", color=TEXT_MUTED)
        return

    screen.blit(image, rect)
    if selected:
        pygame.draw.rect(screen, ACCENT, rect.inflate(4, 4), 2, border_radius=6)


def _row_card_size(row_rect: pygame.Rect, card_count: int) -> tuple[int, int]:
    if card_count <= 0:
        return (110, 165)

    # Target row cards: larger than staged opponent cards.
    width_by_column = round(row_rect.width * 0.86)
    width_by_height = round(row_rect.height * 0.38)
    width = min(210, max(112, min(width_by_column, width_by_height)))
    return (width, round(width * 1.5))


def _row_visible_step(row_rect: pygame.Rect, card_height: int, card_count: int) -> int:
    if card_count <= 1:
        return 0

    available_step = (row_rect.height - 36 - card_height) // max(1, card_count - 1)
    return max(30, min(round(card_height * 0.38), available_step))


def _staged_card_size(opponent_rect: pygame.Rect, opponent_count: int) -> tuple[int, int]:
    if opponent_count <= 0:
        return (66, 99)

    available_height_per_player = opponent_rect.height / opponent_count
    width_by_height = round(available_height_per_player * 0.42)
    width_by_area = round(opponent_rect.width * 0.42)
    width = min(92, max(48, min(width_by_height, width_by_area)))
    return (width, round(width * 1.5))


def _opponent_circle_size(opponent_rect: pygame.Rect, opponent_count: int) -> int:
    if opponent_count <= 0:
        return 32

    available_height_per_player = opponent_rect.height / opponent_count
    return min(58, max(30, round(available_height_per_player * 0.38)))


def _hand_card_size(hand_rect: pygame.Rect, card_count: int) -> tuple[int, int]:
    if card_count <= 0:
        return (120, 180)

    width_by_visible_height = round(hand_rect.height * 1.12)
    width_by_available_space = round(hand_rect.width / max(5.8, card_count * 0.78))
    width = min(205, max(118, min(width_by_visible_height, width_by_available_space)))
    return (width, round(width * 1.5))


def _hand_spacing(hand_rect: pygame.Rect, card_width: int, card_count: int) -> int:
    if card_count <= 1:
        return card_width

    exact_spacing = (hand_rect.width - card_width) // max(1, card_count - 1)
    return max(46, min(round(card_width * 0.96), exact_spacing))


def _initials(name: str) -> str:
    parts = [part for part in name.strip().split() if part]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[-1][0]}".upper()


def _player_color(index: int) -> pygame.Color:
    colors = (
        pygame.Color(216, 83, 83),
        pygame.Color(83, 151, 216),
        pygame.Color(237, 194, 76),
        pygame.Color(122, 197, 104),
        pygame.Color(177, 113, 219),
    )
    return colors[index % len(colors)]


@lru_cache(maxsize=64)
def _scaled_board_image_full(width: int, height: int) -> pygame.Surface | None:
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


@lru_cache(maxsize=256)
def _scaled_card_image(card_value: int, width: int, height: int) -> pygame.Surface | None:
    image = _load_card_image(card_value)
    if image is None:
        return None
    return pygame.transform.smoothscale(image, (width, height))


@lru_cache(maxsize=128)
def _load_card_image(card_value: int) -> pygame.Surface | None:
    image_path = _project_root() / "images" / f"karte_{card_value:03}.png"
    if not image_path.exists():
        return None
    return pygame.image.load(str(image_path)).convert_alpha()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]
