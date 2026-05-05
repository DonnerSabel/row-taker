from __future__ import annotations

from dataclasses import dataclass
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
from row_taker.gui.assets import DEFAULT_GUI_ASSETS, GuiAssets
from row_taker.gui.board_layout import (
    BoardGeometry,
    CardPlacement,
    OpponentSlotGeometry,
    compute_board_geometry,
    hand_card_placements,
    row_card_placements,
)
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import (
    ACCENT,
    CARD_FILL,
    CARD_SELECTED,
    PANEL_BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    PrimitiveDrawer,
)
from row_taker.gui_common.ui.common_render import format_presentation_event
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult


@dataclass(frozen=True, slots=True)
class CardTarget:
    card_value: int
    placement: CardPlacement

    @property
    def rect(self) -> pygame.Rect:
        return self.placement.rect


@dataclass(frozen=True, slots=True)
class RowTarget:
    row_id: object
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class ContinueTarget:
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class OpponentSlot:
    player_id: PlayerID
    player_name: str
    geometry: OpponentSlotGeometry


@dataclass(frozen=True, slots=True)
class GameScreenTargets:
    card_targets: tuple[CardTarget, ...] = ()
    row_targets: tuple[RowTarget, ...] = ()
    continue_target: ContinueTarget | None = None


@dataclass(frozen=True, slots=True)
class GameScreen:
    state: ClientState
    frame_count: int
    last_action_summary: str

    def build_targets(self, layout: DemoLayout) -> GameScreenTargets:
        geometry = _compute_geometry(layout.window_rect, self.state)
        return build_game_screen_targets(geometry, self.state)

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
        geometry = _compute_geometry(layout.window_rect, self.state)
        render_game_screen(
            screen,
            drawer=drawer,
            geometry=geometry,
            client_state=self.state,
            game_targets=targets,
            last_action_summary=self.last_action_summary,
        )


def build_game_screen_targets(geometry: BoardGeometry, state: ClientState) -> GameScreenTargets:
    return GameScreenTargets(
        card_targets=_build_card_targets(geometry, state),
        row_targets=_build_row_targets(geometry, state),
        continue_target=_build_continue_target(geometry, state),
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
    geometry: BoardGeometry,
    client_state: ClientState,
    game_targets: GameScreenTargets,
    last_action_summary: str,
    assets: GuiAssets = DEFAULT_GUI_ASSETS,
) -> None:
    _draw_full_background(screen, geometry.window_rect, assets)
    _draw_rows(screen, drawer, geometry, client_state, game_targets, assets)
    _draw_opponent_slots(screen, drawer, geometry, client_state, assets)
    _draw_hand(screen, drawer, client_state, game_targets, assets)
    _draw_stats_field(screen, drawer, geometry, client_state)
    _draw_status_overlay(screen, drawer, geometry, client_state, last_action_summary, game_targets)


def _compute_geometry(window_rect: pygame.Rect, state: ClientState) -> BoardGeometry:
    public_state = state.public_state
    player_state = state.player_state
    row_count = len(public_state.rows) if public_state is not None else 4
    hand_card_count = len(player_state.hand) if player_state is not None else 0
    opponent_count = len(_opponent_players(state))

    return compute_board_geometry(
        window_rect.size,
        row_count=row_count,
        hand_card_count=hand_card_count,
        opponent_count=opponent_count,
    )


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


def _build_card_targets(geometry: BoardGeometry, state: ClientState) -> tuple[CardTarget, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()

    placements = hand_card_placements(geometry, card_count=len(player_state.hand))
    return tuple(
        CardTarget(card_value=card.value, placement=placement)
        for card, placement in zip(player_state.hand, placements, strict=False)
    )


def _build_row_targets(geometry: BoardGeometry, state: ClientState) -> tuple[RowTarget, ...]:
    public_state = state.public_state
    player_state = state.player_state
    if public_state is None or player_state is None:
        return ()

    if player_state.phase_info.phase != Phase.CHOOSE_ROW:
        return ()

    selectable = set(player_state.get_selectable_row_ids_for_choose_row())
    targets: list[RowTarget] = []
    for row, rect in zip(public_state.rows, geometry.row_columns, strict=False):
        if row.row_id in selectable:
            targets.append(RowTarget(row_id=row.row_id, rect=rect))
    return tuple(targets)


def _build_continue_target(geometry: BoardGeometry, state: ClientState) -> ContinueTarget | None:
    if not state.pending_presentation_events:
        return None

    rect = pygame.Rect(
        geometry.stats_rect.left + 12,
        geometry.stats_rect.bottom - 46,
        max(1, geometry.stats_rect.width - 24),
        34,
    )
    return ContinueTarget(rect=rect)


def _draw_full_background(screen: pygame.Surface, window_rect: pygame.Rect, assets: GuiAssets) -> None:
    board = assets.scaled_board_image_full(window_rect.width, window_rect.height)
    if board is None:
        screen.fill((18, 84, 38))
        return

    # board.png is the full background. No cropping, aspect ratio ignored.
    screen.blit(board, window_rect.topleft)


def _draw_rows(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    client_state: ClientState,
    game_targets: GameScreenTargets,
    assets: GuiAssets,
) -> None:
    public_state = client_state.public_state
    if public_state is None:
        return

    row_target_by_id = {target.row_id: target for target in game_targets.row_targets}

    for row_index, (row, column_rect) in enumerate(zip(public_state.rows, geometry.row_columns, strict=False)):
        selectable = row.row_id in row_target_by_id
        placements = row_card_placements(geometry, row_index=row_index, card_count=len(row.cards))
        _draw_row_column(
            screen,
            drawer,
            column_rect,
            row_id=row.row_id,
            cards=row.cards,
            placements=placements,
            selectable=selectable,
            assets=assets,
        )


def _draw_row_column(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    row_id: object,
    cards: tuple[Any, ...],
    placements: tuple[CardPlacement, ...],
    selectable: bool,
    assets: GuiAssets,
) -> None:
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

    for card, placement in zip(cards, placements, strict=False):
        _draw_card_image_or_fallback(screen, drawer, placement.rect, card, selected=selectable, assets=assets)


def _draw_opponent_slots(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    client_state: ClientState,
    assets: GuiAssets,
) -> None:
    revealed_by_player = _revealed_card_values_by_player(client_state)
    opponents = _opponent_slot_data(client_state, geometry)

    for index, slot in enumerate(opponents):
        color = _player_color(index)
        circle_rect = slot.geometry.circle_rect
        pygame.draw.ellipse(screen, color, circle_rect)
        pygame.draw.ellipse(screen, pygame.Color(255, 255, 255, 150), circle_rect, 2)

        initials = _initials(slot.player_name)
        drawer.draw_text(
            screen,
            initials,
            (circle_rect.centerx - 8, circle_rect.centery - 8),
            role="tiny",
            color=TEXT_PRIMARY,
        )

        card_value = revealed_by_player.get(slot.player_id)
        staged_rect = slot.geometry.staged_card.rect
        if card_value is None:
            _draw_staged_card_back(screen, staged_rect)
        else:
            _draw_card_value_image_or_back(screen, drawer, staged_rect, card_value, assets)


def _opponent_slot_data(client_state: ClientState, geometry: BoardGeometry) -> tuple[OpponentSlot, ...]:
    players = _opponent_players(client_state)
    return tuple(
        OpponentSlot(
            player_id=player.player_id,
            player_name=player.name,
            geometry=slot_geometry,
        )
        for player, slot_geometry in zip(players, geometry.opponent_slots, strict=False)
    )


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
    assets: GuiAssets,
) -> None:
    image = assets.scaled_card_image(card_value, rect.width, rect.height)
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
    assets: GuiAssets,
) -> None:
    player_state = client_state.player_state
    if player_state is None:
        return

    target_by_value = {target.card_value: target for target in game_targets.card_targets}
    for card in player_state.hand:
        target = target_by_value.get(card.value)
        if target is None:
            continue
        _draw_card_image_or_fallback(screen, drawer, target.rect, card, assets=assets)

    if (
        player_state.phase_info.phase == Phase.CHOOSE_ROW
        and player_state.pending_card_value() is not None
        and game_targets.card_targets
    ):
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
    geometry: BoardGeometry,
    client_state: ClientState,
) -> None:
    rect = geometry.stats_rect
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
    geometry: BoardGeometry,
    client_state: ClientState,
    last_action_summary: str,
    game_targets: GameScreenTargets,
) -> None:
    _draw_overlay_box(screen, geometry.overlay_rect)

    player_state = client_state.player_state
    phase = player_state.phase_info.phase.value if player_state is not None else "-"
    player_name = player_state.self_player_name() if player_state is not None else "-"

    line_1 = f"{player_name}  |  Phase: {phase}  |  Aktion: {client_state.pending_action.value}"
    drawer.draw_text(
        screen,
        line_1,
        (geometry.overlay_rect.left + 10, geometry.overlay_rect.top + 8),
        role="small",
    )

    line_2 = client_state.flash_message.text if client_state.flash_message is not None else last_action_summary
    drawer.draw_text(
        screen,
        line_2,
        (geometry.overlay_rect.left + 10, geometry.overlay_rect.top + 30),
        role="tiny",
        color=TEXT_MUTED,
    )

    if client_state.pending_presentation_events:
        events_rect = pygame.Rect(
            geometry.stats_rect.left,
            geometry.stats_rect.bottom - 142,
            geometry.stats_rect.width,
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
    assets: GuiAssets,
) -> None:
    image = assets.scaled_card_image(card.value, rect.width, rect.height)
    if image is None:
        pygame.draw.rect(screen, CARD_SELECTED if selected else CARD_FILL, rect, border_radius=6)
        pygame.draw.rect(screen, ACCENT if selected else PANEL_BORDER, rect, 2 if selected else 1, border_radius=6)
        drawer.draw_text(screen, str(card.value), (rect.left + 8, rect.top + 6), role="body")
        drawer.draw_text(screen, f"{card.bullheads} bh", (rect.left + 8, rect.top + 30), role="small", color=TEXT_MUTED)
        return

    screen.blit(image, rect)
    if selected:
        pygame.draw.rect(screen, ACCENT, rect.inflate(4, 4), 2, border_radius=6)


def _opponent_players(state: ClientState) -> tuple[Any, ...]:
    public_state = state.public_state
    if public_state is None:
        return ()
    return tuple(player for player in public_state.players if player.player_id != state.own_player_id)


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
