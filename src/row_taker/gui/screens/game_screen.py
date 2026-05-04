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
class BoardLayout:
    window_rect: pygame.Rect
    row_rects: tuple[pygame.Rect, ...]
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
        return handle_game_event(
            event,
            state=self.state,
            game_targets=targets,
        )

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
    _draw_hand(screen, drawer, client_state, game_targets)
    _draw_status_overlay(screen, drawer, board_layout, client_state, last_action_summary, game_targets)


def _handle_left_click(position: tuple[int, int], *, game_targets: GameScreenTargets) -> ScreenResult:
    # Handkarten liegen visuell übereinander. Deshalb von hinten nach vorne prüfen.
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

    # Schülerlayout:
    # - board.png ist der komplette Fensterhintergrund.
    # - Die vier Reihen liegen nebeneinander als Spalten.
    # - Jede Reihe wächst von oben nach unten.
    # - Unten bleibt der Rahmen für die Handkarten.
    margin_x = max(20, round(window_rect.width * 0.025))
    top_margin = max(64, round(window_rect.height * 0.09))
    hand_visible_height = max(120, round(window_rect.height * 0.22))
    bottom_margin = max(8, round(window_rect.height * 0.012))

    row_area_top = top_margin
    row_area_bottom = window_rect.height - hand_visible_height - bottom_margin
    row_area_height = max(260, row_area_bottom - row_area_top)
    row_area_width = window_rect.width - 2 * margin_x

    column_gap = max(10, round(row_area_width * 0.018))
    column_count = max(1, row_count)
    column_width = max(90, (row_area_width - (column_count - 1) * column_gap) // column_count)

    row_rects = tuple(
        pygame.Rect(
            margin_x + index * (column_width + column_gap),
            row_area_top,
            column_width,
            row_area_height,
        )
        for index in range(column_count)
    )

    hand_rect = pygame.Rect(
        margin_x,
        window_rect.height - hand_visible_height,
        window_rect.width - 2 * margin_x,
        hand_visible_height,
    )

    overlay_rect = pygame.Rect(
        margin_x,
        10,
        min(680, window_rect.width - 2 * margin_x),
        max(44, top_margin - 20),
    )

    return BoardLayout(
        window_rect=window_rect,
        row_rects=row_rects,
        hand_rect=hand_rect,
        overlay_rect=overlay_rect,
    )


def _build_card_targets(board_layout: BoardLayout, state: ClientState) -> tuple[CardTarget, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()

    card_count = len(player_state.hand)
    if card_count == 0:
        return ()

    card_width, card_height = _hand_card_size(board_layout.hand_rect, card_count)
    spacing = _hand_spacing(board_layout.hand_rect, card_width, card_count)

    # Schülerlayout: Die Handkarten sitzen unten im Rahmen.
    # Nur die obere Kartenhälfte ist sichtbar.
    x_start = board_layout.hand_rect.centerx - (
        (card_count - 1) * spacing + card_width
    ) // 2
    x_start = max(board_layout.hand_rect.left, x_start)
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
        board_layout.window_rect.right - 210,
        board_layout.window_rect.top + 16,
        190,
        34,
    )
    return ContinueTarget(rect=rect)


def _draw_full_background(screen: pygame.Surface, window_rect: pygame.Rect) -> None:
    board = _scaled_board_image_full(window_rect.width, window_rect.height)
    if board is None:
        screen.fill((18, 84, 38))
        return

    # Schülerlayout: board.png ist der komplette Hintergrund.
    # Kein Cropping, Aspect Ratio ist hier bewusst egal.
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
        _draw_overlay_box(screen, board_layout.overlay_rect)
        drawer.draw_text(
            screen,
            "Kein Spielzustand vorhanden.",
            (board_layout.overlay_rect.left + 10, board_layout.overlay_rect.top + 9),
            role="body",
        )
        return

    row_target_by_id = {target.row_id: target for target in game_targets.row_targets}

    for row, row_rect in zip(public_state.rows, board_layout.row_rects, strict=False):
        selectable = row.row_id in row_target_by_id
        _draw_row_lane(screen, drawer, row_rect, row_id=row.row_id, cards=row.cards, selectable=selectable)


def _draw_row_lane(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    row_id: object,
    cards: tuple[Any, ...],
    selectable: bool,
) -> None:
    # Vier Spalten nebeneinander; jede Spalte ist eine Reihe.
    lane_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(lane_surface, pygame.Color(0, 0, 0, 30), lane_surface.get_rect(), border_radius=10)
    screen.blit(lane_surface, rect)

    border = ACCENT if selectable else pygame.Color(255, 255, 255, 38)
    pygame.draw.rect(screen, border, rect, 3 if selectable else 1, border_radius=10)

    drawer.draw_text(
        screen,
        f"Reihe {row_id}",
        (rect.left + 8, rect.top + 6),
        role="small",
        color=ACCENT if selectable else TEXT_MUTED,
    )

    bullheads = sum(card.bullheads for card in cards)
    drawer.draw_text(
        screen,
        f"{bullheads}",
        (rect.right - 34, rect.top + 6),
        role="small",
        color=TEXT_MUTED,
    )

    if not cards:
        return

    card_width = _row_card_width(rect, len(cards))
    card_height = round(card_width * 1.5)

    # Schülerlayout: Karten einer Reihe wachsen von oben nach unten.
    # Die Karten überdecken sich; oben bleiben Zahl und Hornochsen sichtbar.
    x = rect.centerx - card_width // 2
    y = rect.top + 32
    visible_step = _row_visible_step(rect, card_height, len(cards))

    for index, card in enumerate(cards):
        card_rect = pygame.Rect(
            x,
            y + index * visible_step,
            card_width,
            card_height,
        )
        _draw_card_image_or_fallback(screen, drawer, card_rect, card, selected=selectable)


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
        pending_rect = pygame.Rect(24, client_state_overlay_y(game_targets), 250, 34)
        _draw_overlay_box(screen, pending_rect)
        drawer.draw_text(
            screen,
            f"Reihe für Karte {player_state.pending_card_value()} wählen",
            (pending_rect.left + 10, pending_rect.top + 8),
            role="small",
            color=ACCENT,
        )


def client_state_overlay_y(game_targets: GameScreenTargets) -> int:
    if game_targets.card_targets:
        return max(60, game_targets.card_targets[0].rect.top - 42)
    return 60


def _draw_status_overlay(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    board_layout: BoardLayout,
    client_state: ClientState,
    last_action_summary: str,
    game_targets: GameScreenTargets,
) -> None:
    _draw_overlay_box(screen, board_layout.overlay_rect)

    public_state = client_state.public_state
    player_state = client_state.player_state
    phase = player_state.phase_info.phase.value if player_state is not None else "-"
    player_name = player_state.self_player_name() if player_state is not None else "-"

    score_parts: list[str] = []
    if public_state is not None:
        for player in public_state.players:
            marker = "★" if player.player_id == client_state.own_player_id else ""
            score_parts.append(f"{marker}{player.name}: {player.score}")

    line_1 = f"{player_name}  |  Phase: {phase}  |  Aktion: {client_state.pending_action.value}"
    line_2 = "   ".join(score_parts) if score_parts else last_action_summary

    drawer.draw_text(screen, line_1, (board_layout.overlay_rect.left + 10, board_layout.overlay_rect.top + 8), role="small")
    drawer.draw_text(
        screen,
        line_2,
        (board_layout.overlay_rect.left + 10, board_layout.overlay_rect.top + 30),
        role="tiny",
        color=TEXT_MUTED,
    )

    if client_state.flash_message is not None:
        flash_rect = pygame.Rect(
            board_layout.overlay_rect.left,
            board_layout.overlay_rect.bottom + 8,
            min(560, board_layout.window_rect.width - 48),
            34,
        )
        _draw_overlay_box(screen, flash_rect)
        drawer.draw_text(
            screen,
            client_state.flash_message.text,
            (flash_rect.left + 10, flash_rect.top + 8),
            role="small",
            color=ACCENT,
        )

    if client_state.pending_presentation_events:
        events_rect = pygame.Rect(
            board_layout.window_rect.right - 330,
            board_layout.window_rect.top + 60,
            306,
            120,
        )
        _draw_overlay_box(screen, events_rect)
        lines = [format_presentation_event(event) for event in client_state.pending_presentation_events[:4]]
        drawer.draw_wrapped_lines(
            screen,
            lines,
            events_rect.inflate(-18, -18),
            role="small",
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
    pygame.draw.rect(overlay, pygame.Color(0, 0, 0, 145), overlay.get_rect(), border_radius=8)
    screen.blit(overlay, rect)
    pygame.draw.rect(screen, pygame.Color(255, 255, 255, 60), rect, 1, border_radius=8)


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

    image_rect = image.get_rect(center=rect.center)
    screen.blit(image, image_rect)
    if selected:
        pygame.draw.rect(screen, ACCENT, image_rect.inflate(4, 4), 2, border_radius=6)


def _row_card_width(row_rect: pygame.Rect, card_count: int) -> int:
    # Eine Reihe ist eine Spalte. Karten sollen dort möglichst groß sein,
    # aber in die Spaltenbreite passen.
    by_width = max(80, round(row_rect.width * 0.82))
    by_height = max(80, round(row_rect.height * 0.34))
    return min(190, max(100, min(by_width, by_height)))


def _row_visible_step(row_rect: pygame.Rect, card_height: int, card_count: int) -> int:
    if card_count <= 1:
        return 0

    available_step = (row_rect.height - 34 - card_height) // max(1, card_count - 1)
    # Der obere Teil jeder Karte bleibt sichtbar; bei Platznot stärker überdecken.
    return max(30, min(round(card_height * 0.38), available_step))


def _hand_card_size(hand_rect: pygame.Rect, card_count: int) -> tuple[int, int]:
    if card_count <= 0:
        return (120, 180)

    # Die Handkarten sollen den unteren Rahmen gut ausnutzen.
    # Da nur die obere Hälfte sichtbar ist, darf die Karte höher sein als der Rahmen.
    width_by_visible_height = max(105, round(hand_rect.height * 1.12))
    width_by_available_space = max(105, round(hand_rect.width / max(5.8, card_count * 0.78)))
    width = min(205, max(125, min(width_by_visible_height, width_by_available_space)))
    return (width, round(width * 1.5))


def _hand_spacing(hand_rect: pygame.Rect, card_width: int, card_count: int) -> int:
    if card_count <= 1:
        return card_width

    exact_spacing = (hand_rect.width - card_width) // max(1, card_count - 1)
    # Möglichst gleichmäßig über den unteren Rahmen verteilen.
    # Bei vielen Karten darf es überlappen, aber nicht zu stark.
    return max(48, min(round(card_width * 0.95), exact_spacing))


@lru_cache(maxsize=64)
def _scaled_board_image_full(width: int, height: int) -> pygame.Surface | None:
    image = _load_board_image()
    if image is None:
        return None

    # Schülerlayout: kein Letterboxing, kein Cropping.
    # Das Boardbild wird direkt auf die Fenstergröße skaliert.
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
