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
from row_taker.gui import constants as c
from row_taker.gui_demo.layout import DemoLayout
from row_taker.gui_demo.primitives import ACCENT, TEXT_MUTED, WINDOW_BACKGROUND, PrimitiveDrawer
from row_taker.gui_demo.ui.common_render import (
    format_presentation_event,
    render_standard_footer,
    render_standard_header,
)
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
class GuiBoardGeometry:
    board_rect: pygame.Rect
    play_rect: pygame.Rect
    row_rects: tuple[pygame.Rect, ...]


@dataclass(frozen=True, slots=True)
class GameScreen:
    state: ClientState
    frame_count: int
    last_action_summary: str

    def build_targets(self, layout: DemoLayout) -> GameScreenTargets:
        return build_game_screen_targets(layout, self.state)

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
        render_game_screen(
            screen,
            drawer=drawer,
            layout=layout,
            client_state=self.state,
            frame_count=self.frame_count,
            game_targets=targets,
            last_action_summary=self.last_action_summary,
        )


def build_game_screen_targets(layout: DemoLayout, state: ClientState) -> GameScreenTargets:
    return GameScreenTargets(
        card_targets=_build_card_targets(layout, state),
        row_targets=_build_row_targets(layout, state),
        continue_target=_build_continue_target(layout, state),
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
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    game_targets: GameScreenTargets,
    last_action_summary: str,
) -> None:
    screen.fill(WINDOW_BACKGROUND)
    render_standard_header(screen, drawer, layout, client_state)
    _render_board_panel(screen, drawer, layout, client_state, game_targets)
    _render_hand_panel(screen, drawer, layout, client_state, game_targets)
    _render_sidebar(screen, drawer, layout, client_state, frame_count, last_action_summary, game_targets)
    render_standard_footer(screen, drawer, layout)


def _handle_left_click(position: tuple[int, int], *, game_targets: GameScreenTargets) -> ScreenResult:
    for target in game_targets.card_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseCard(card_value=target.card_value))

    for target in game_targets.row_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseRow(row_id=target.row_id))

    if game_targets.continue_target is not None and game_targets.continue_target.rect.collidepoint(position):
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    return NO_SCREEN_RESULT


def _build_card_targets(layout: DemoLayout, state: ClientState) -> tuple[CardTarget, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()

    hand_content = _content_rect(layout.main_bottom_rect)
    hand_cards_rect = hand_content.inflate(-12, -12)
    hand_cards_rect.top += 44
    hand_cards_rect.height = max(1, hand_cards_rect.height - 44)

    card_size = _hand_card_size(hand_cards_rect, len(player_state.hand))
    card_width, card_height = card_size
    gap = max(8, min(22, card_width // 5))
    columns = max(1, hand_cards_rect.width // (card_width + gap))

    targets: list[CardTarget] = []
    for index, card in enumerate(player_state.hand):
        row_index = index // columns
        column_index = index % columns
        rect = pygame.Rect(
            hand_cards_rect.left + column_index * (card_width + gap),
            hand_cards_rect.top + row_index * (card_height + gap),
            card_width,
            card_height,
        )
        targets.append(CardTarget(card_value=card.value, rect=rect))
    return tuple(targets)


def _build_row_targets(layout: DemoLayout, state: ClientState) -> tuple[RowTarget, ...]:
    public_state = state.public_state
    player_state = state.player_state
    if public_state is None or player_state is None:
        return ()
    if player_state.phase_info.phase != Phase.CHOOSE_ROW:
        return ()

    geometry = _board_geometry(layout, len(public_state.rows))
    selectable = set(player_state.get_selectable_row_ids_for_choose_row())

    targets: list[RowTarget] = []
    for row, rect in zip(public_state.rows, geometry.row_rects, strict=False):
        if row.row_id in selectable:
            targets.append(RowTarget(row_id=row.row_id, rect=rect))
    return tuple(targets)


def _build_continue_target(layout: DemoLayout, state: ClientState) -> ContinueTarget | None:
    if not state.pending_presentation_events:
        return None
    rect = pygame.Rect(
        layout.sidebar_rect.left + 20,
        layout.sidebar_rect.bottom - 54,
        layout.sidebar_rect.width - 40,
        34,
    )
    return ContinueTarget(rect=rect)


def _render_board_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    game_targets: GameScreenTargets,
) -> None:
    content = drawer.draw_panel(screen, layout.main_top_rect, title="Spielfeld")
    public_state = client_state.public_state

    if public_state is None:
        drawer.draw_wrapped_lines(screen, ["Kein public_state verfügbar."], content)
        return

    geometry = _board_geometry(layout, len(public_state.rows))
    _draw_board_background(screen, geometry.board_rect)

    row_target_by_id = {target.row_id: target for target in game_targets.row_targets}
    for row, row_rect in zip(public_state.rows, geometry.row_rects, strict=False):
        selectable = row.row_id in row_target_by_id
        _draw_board_row(
            screen,
            drawer,
            row_rect,
            row_id=row.row_id,
            cards=row.cards,
            selectable=selectable,
        )

    _draw_score_strip(screen, drawer, content, client_state)


def _render_hand_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    game_targets: GameScreenTargets,
) -> None:
    content = drawer.draw_panel(screen, layout.main_bottom_rect, title="Eigene Hand")
    player_state = client_state.player_state

    if player_state is None:
        drawer.draw_wrapped_lines(screen, ["Kein player_state verfügbar."], content)
        return

    info_lines = [
        f"Spieler: {player_state.self_player_name()}",
        f"Aktion: {client_state.pending_action.value}",
        "Klicke eine Karte, um sie auszuwählen.",
    ]
    if player_state.phase_info.phase == Phase.CHOOSE_ROW and player_state.pending_card_value() is not None:
        info_lines.append(f"Ausliegende Karte: {player_state.pending_card_value()}")

    info_rect = content.copy()
    info_rect.height = 42
    drawer.draw_wrapped_lines(screen, info_lines, info_rect, role="small", color=TEXT_MUTED)

    target_by_value = {target.card_value: target for target in game_targets.card_targets}
    for card in player_state.hand:
        target = target_by_value.get(card.value)
        if target is None:
            continue
        _draw_card_image_or_fallback(screen, drawer, target.rect, card)

    if player_state.phase_info.phase == Phase.CHOOSE_ROW and player_state.pending_card_value() is not None:
        hint_rect = pygame.Rect(content.right - 170, content.top, 150, 32)
        drawer.draw_badge(screen, hint_rect, text=f"Reihe wählen: {player_state.pending_card_value()}", active=True)


def _draw_board_row(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    row_id: object,
    cards: tuple[Any, ...],
    selectable: bool,
) -> None:
    border_color = ACCENT if selectable else TEXT_MUTED
    pygame.draw.rect(screen, (8, 20, 12), rect, border_radius=10)
    pygame.draw.rect(screen, border_color, rect, 2 if selectable else 1, border_radius=10)

    title_rect = pygame.Rect(rect.left + 8, rect.top + 6, 90, 22)
    drawer.draw_text(screen, str(row_id), title_rect.topleft, role="small", color=border_color)

    bullheads = sum(card.bullheads for card in cards)
    drawer.draw_text(
        screen,
        f"{bullheads} Hornochsen",
        (rect.right - 112, rect.top + 6),
        role="small",
        color=TEXT_MUTED,
    )

    if not cards:
        return

    card_gap = 8
    max_width = max(36, (rect.width - 20 - (len(cards) - 1) * card_gap) // max(1, len(cards)))
    card_width = min(72, max_width)
    card_height = round(card_width * 1.5)
    y = rect.centery - card_height // 2

    for index, card in enumerate(cards):
        card_rect = pygame.Rect(
            rect.left + 10 + index * (card_width + card_gap),
            y,
            card_width,
            card_height,
        )
        _draw_card_image_or_fallback(screen, drawer, card_rect, card, selected=selectable)


def _draw_score_strip(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    content: pygame.Rect,
    client_state: ClientState,
) -> None:
    public_state = client_state.public_state
    if public_state is None:
        return

    y = content.bottom - 30
    x = content.left
    for player in public_state.players:
        marker = " ★" if player.player_id == client_state.own_player_id else ""
        text = f"{player.name}: {player.score}{marker}"
        drawer.draw_text(screen, text, (x, y), role="small", color=ACCENT if marker else TEXT_MUTED)
        x += max(130, len(text) * 8)


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
        drawer.draw_card(screen, rect, value=card.value, bullheads=card.bullheads, selected=selected)
        return

    image_rect = image.get_rect(center=rect.center)
    screen.blit(image, image_rect)
    if selected:
        pygame.draw.rect(screen, ACCENT, image_rect.inflate(4, 4), 2, border_radius=6)


def _board_geometry(layout: DemoLayout, row_count: int) -> GuiBoardGeometry:
    content = _content_rect(layout.main_top_rect)
    board_rect = _fit_rect(_board_image_size(), content)

    play_rect = pygame.Rect(
        board_rect.left + round(board_rect.width * c.BOARD_PLAY_AREA_X_RATIO),
        board_rect.top + round(board_rect.height * c.BOARD_PLAY_AREA_Y_RATIO),
        round(board_rect.width * c.BOARD_PLAY_AREA_WIDTH_RATIO),
        round(board_rect.height * c.BOARD_PLAY_AREA_HEIGHT_RATIO),
    )

    rows = max(1, row_count)
    row_gap = max(8, play_rect.height // 40)
    row_height = max(44, (play_rect.height - (rows - 1) * row_gap) // rows)

    row_rects = tuple(
        pygame.Rect(
            play_rect.left,
            play_rect.top + index * (row_height + row_gap),
            play_rect.width,
            row_height,
        )
        for index in range(rows)
    )

    return GuiBoardGeometry(board_rect=board_rect, play_rect=play_rect, row_rects=row_rects)


def _content_rect(panel_rect: pygame.Rect) -> pygame.Rect:
    rect = panel_rect.inflate(-24, -44)
    rect.top += 20
    return rect


def _fit_rect(source_size: tuple[int, int], target: pygame.Rect) -> pygame.Rect:
    source_width, source_height = source_size
    if source_width <= 0 or source_height <= 0:
        return target.copy()

    scale = min(target.width / source_width, target.height / source_height)
    width = max(1, round(source_width * scale))
    height = max(1, round(source_height * scale))
    rect = pygame.Rect(0, 0, width, height)
    rect.center = target.center
    return rect


def _hand_card_size(rect: pygame.Rect, card_count: int) -> tuple[int, int]:
    if card_count <= 0:
        return (72, 108)

    columns = min(card_count, 10)
    width_by_columns = (rect.width - (columns - 1) * 10) // max(1, columns)
    width_by_height = max(36, (rect.height - 10) * 2 // 3)
    width = max(44, min(96, width_by_columns, width_by_height))
    return (width, round(width * 1.5))


def _draw_board_background(screen: pygame.Surface, board_rect: pygame.Rect) -> None:
    board = _scaled_board_image(board_rect.width, board_rect.height)
    if board is None:
        pygame.draw.rect(screen, (20, 70, 32), board_rect, border_radius=12)
        pygame.draw.rect(screen, ACCENT, board_rect, 1, border_radius=12)
        return
    screen.blit(board, board_rect)


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


@lru_cache(maxsize=1)
def _board_image_size() -> tuple[int, int]:
    image = _load_board_image()
    if image is None:
        return (1200, 800)
    return image.get_size()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _render_sidebar(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    last_action_summary: str,
    game_targets: GameScreenTargets,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.sidebar_rect, title="Zustandsübersicht")
    y = content_rect.top

    entries = [
        ("client_mode", client_state.client_mode.value),
        ("pending_action", client_state.pending_action.value),
        ("own_client_id", client_state.own_client_id or "-"),
        ("own_player_id", client_state.own_player_id or "-"),
        ("session_error", client_state.session_error or "-"),
        ("presentation", str(len(client_state.pending_presentation_events))),
        ("frame", str(frame_count)),
    ]

    for key, value in entries:
        drawer.draw_key_value(screen, key, value, (content_rect.left, y))
        y += 28

    drawer.draw_text(screen, "last_gui_action", (content_rect.left, y + 6), role="small", color=TEXT_MUTED)
    action_rect = content_rect.copy()
    action_rect.top = y + 28
    action_rect.height = 72
    drawer.draw_wrapped_lines(screen, [last_action_summary], action_rect, role="small", color=ACCENT)

    flash_text = client_state.flash_message.text if client_state.flash_message is not None else "Keine Meldung"
    drawer.draw_text(screen, "flash_message", (content_rect.left, action_rect.bottom + 10), role="small", color=TEXT_MUTED)
    flash_rect = content_rect.copy()
    flash_rect.top = action_rect.bottom + 32
    flash_rect.height = 64
    drawer.draw_wrapped_lines(screen, [flash_text], flash_rect, role="body", color=ACCENT)

    events_rect = content_rect.copy()
    events_rect.top = flash_rect.bottom + 18
    events_bottom = layout.sidebar_rect.bottom - 70
    events_rect.height = max(40, events_bottom - events_rect.top)
    drawer.draw_text(screen, "presentation events", (events_rect.left, events_rect.top), role="small", color=TEXT_MUTED)
    events_rect.top += 22
    event_lines = [format_presentation_event(event) for event in client_state.pending_presentation_events]
    if not event_lines:
        event_lines = ["Keine ausstehenden Präsentationsereignisse."]
    drawer.draw_wrapped_lines(screen, event_lines, events_rect, role="small")

    if game_targets.continue_target is not None:
        drawer.draw_badge(screen, game_targets.continue_target.rect, text="Weiter [Leertaste]", active=True)
