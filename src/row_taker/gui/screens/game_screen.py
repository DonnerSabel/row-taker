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
from row_taker.gui.animation import AnimationClock, lerp_rect
from row_taker.gui.assets import DEFAULT_GUI_ASSETS, GuiAssets
from row_taker.gui.board_layout import (
    BoardGeometry,
    CardPlacement,
    OpponentSlotGeometry,
    compute_board_geometry,
    hand_card_placements,
    row_card_placements,
)
from row_taker.gui.card import GuiCard, draw_card_back
from row_taker.gui.presentation_visuals import PresentationVisuals, build_presentation_visuals
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_badge, draw_button, draw_overlay_panel
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import PrimitiveDrawer
from row_taker.gui_common.ui.screen_result import NO_SCREEN_RESULT, ScreenResult

THEME = DEFAULT_THEME
PALETTE = THEME.palette


@dataclass(frozen=True, slots=True)
class CardTarget:
    card: GuiCard

    @property
    def card_value(self) -> int:
        return self.card.card_value

    @property
    def rect(self) -> pygame.Rect:
        return self.card.rect

    def contains_point(self, position: tuple[int, int]) -> bool:
        return self.card.contains_point(position)


@dataclass(frozen=True, slots=True)
class RowTarget:
    row_id: object
    rect: pygame.Rect
    hovered: bool = False


@dataclass(frozen=True, slots=True)
class ContinueTarget:
    rect: pygame.Rect
    hovered: bool = False


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
    presentation_frame_count: int
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
            frame_count=self.frame_count,
            presentation_frame_count=self.presentation_frame_count,
            last_action_summary=self.last_action_summary,
        )


def build_game_screen_targets(geometry: BoardGeometry, state: ClientState) -> GameScreenTargets:
    mouse_pos = pygame.mouse.get_pos()
    return GameScreenTargets(
        card_targets=_build_card_targets(geometry, state, mouse_pos=mouse_pos),
        row_targets=_build_row_targets(geometry, state, mouse_pos=mouse_pos),
        continue_target=_build_continue_target(geometry, state, mouse_pos=mouse_pos),
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
    frame_count: int,
    presentation_frame_count: int,
    last_action_summary: str,
    assets: GuiAssets = DEFAULT_GUI_ASSETS,
) -> None:
    presentation_visuals = build_presentation_visuals(client_state)
    frame_clock = AnimationClock(frame_count)
    presentation_clock = AnimationClock(presentation_frame_count)

    _draw_full_background(screen, geometry.window_rect, assets)
    _draw_rows(screen, drawer, geometry, client_state, game_targets, assets, presentation_visuals, presentation_clock)
    _draw_opponent_slots(screen, drawer, geometry, client_state, assets, presentation_visuals, presentation_clock)
    _draw_hand(screen, drawer, client_state, game_targets, assets, presentation_visuals)
    _draw_presentation_card_motion(
        screen,
        drawer,
        geometry,
        client_state,
        game_targets,
        presentation_visuals,
        assets,
        presentation_clock,
    )
    _draw_stats_field(screen, drawer, geometry, client_state)
    _draw_status_overlay(
        screen,
        drawer,
        geometry,
        client_state,
        last_action_summary,
        game_targets,
        presentation_visuals,
        assets,
        presentation_clock,
    )


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
        if target.contains_point(position):
            return ScreenResult(client_action=ClientActionChooseCard(card_value=target.card_value))

    for target in game_targets.row_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseRow(row_id=target.row_id))

    if game_targets.continue_target is not None and game_targets.continue_target.rect.collidepoint(position):
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    return NO_SCREEN_RESULT


def _build_card_targets(
    geometry: BoardGeometry,
    state: ClientState,
    *,
    mouse_pos: tuple[int, int],
) -> tuple[CardTarget, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()

    placements = hand_card_placements(geometry, card_count=len(player_state.hand))
    hovered_value = _hovered_hand_card_value(tuple(zip(player_state.hand, placements, strict=False)), mouse_pos)
    return tuple(
        CardTarget(
            card=GuiCard.from_card(
                card,
                placement.rect,
                hovered=int(card.value) == hovered_value,
            )
        )
        for card, placement in zip(player_state.hand, placements, strict=False)
    )


def _hovered_hand_card_value(
    cards_with_placements: tuple[tuple[Any, CardPlacement], ...],
    mouse_pos: tuple[int, int],
) -> int | None:
    # Hand cards overlap. Only the visually front-most card should react.
    for card, placement in reversed(cards_with_placements):
        if placement.rect.collidepoint(mouse_pos):
            return int(card.value)
    return None


def _build_row_targets(
    geometry: BoardGeometry,
    state: ClientState,
    *,
    mouse_pos: tuple[int, int],
) -> tuple[RowTarget, ...]:
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
            targets.append(RowTarget(row_id=row.row_id, rect=rect, hovered=rect.collidepoint(mouse_pos)))
    return tuple(targets)


def _build_continue_target(
    geometry: BoardGeometry,
    state: ClientState,
    *,
    mouse_pos: tuple[int, int],
) -> ContinueTarget | None:
    if not state.pending_presentation_events:
        return None

    rect = pygame.Rect(
        geometry.stats_rect.left + 12,
        geometry.stats_rect.bottom - 46,
        max(1, geometry.stats_rect.width - 24),
        34,
    )
    return ContinueTarget(rect=rect, hovered=rect.collidepoint(mouse_pos))


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
    presentation_visuals: PresentationVisuals,
    animation_clock: AnimationClock,
) -> None:
    public_state = client_state.public_state
    if public_state is None:
        return

    row_target_by_id = {target.row_id: target for target in game_targets.row_targets}

    for row_index, (row, column_rect) in enumerate(zip(public_state.rows, geometry.row_columns, strict=False)):
        target = row_target_by_id.get(row.row_id)
        selectable = target is not None
        hovered = bool(target.hovered) if target is not None else False
        placements = row_card_placements(geometry, row_index=row_index, card_count=len(row.cards))
        _draw_row_column(
            screen,
            drawer,
            column_rect,
            row_id=row.row_id,
            cards=row.cards,
            placements=placements,
            selectable=selectable,
            hovered=hovered,
            assets=assets,
            presentation_visuals=presentation_visuals,
            animation_clock=animation_clock,
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
    hovered: bool,
    assets: GuiAssets,
    presentation_visuals: PresentationVisuals,
    animation_clock: AnimationClock,
) -> None:
    lane_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    emphasis = presentation_visuals.row_emphasis_for(row_id)
    lane_fill = PALETTE.lane_overlay_active if emphasis != "none" or hovered else PALETTE.lane_overlay
    pygame.draw.rect(lane_surface, lane_fill, lane_surface.get_rect(), border_radius=8)
    screen.blit(lane_surface, rect)

    border = _row_border_color(selectable=selectable, hovered=hovered, emphasis=emphasis)
    if emphasis != "none":
        _draw_pulsing_outline(screen, rect, border, animation_clock, max_inflate=12)
    border_width = 4 if emphasis != "none" or hovered else 3 if selectable else 1
    pygame.draw.rect(screen, border, rect, border_width, border_radius=8)

    label_color = border if selectable or hovered or emphasis != "none" else PALETTE.text_muted
    drawer.draw_text(screen, str(row_id), (rect.left + 8, rect.top + 6), role="small", color=label_color)

    if emphasis in {"taken", "overflow"}:
        _draw_row_taken_badge(screen, drawer, rect, presentation_visuals)

    for card, placement in zip(cards, placements, strict=False):
        selected = selectable or hovered or emphasis != "none"
        GuiCard.from_card(card, placement.rect, selected=selected).draw(screen, drawer=drawer, assets=assets)


def _row_border_color(*, selectable: bool, hovered: bool, emphasis: str) -> pygame.Color:
    if emphasis == "placed":
        return PALETTE.row_placed
    if emphasis == "choice":
        return PALETTE.row_choice
    if emphasis == "taken":
        return PALETTE.row_taken
    if emphasis == "overflow":
        return PALETTE.row_overflow
    if hovered:
        return PALETTE.accent_hover
    if selectable:
        return PALETTE.accent
    return PALETTE.row_neutral


def _draw_row_taken_badge(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    presentation_visuals: PresentationVisuals,
) -> None:
    cards = ", ".join(str(value) for value in presentation_visuals.taken_card_values)
    if not cards:
        return

    badge_rect = pygame.Rect(rect.left + 8, rect.bottom - 34, max(1, rect.width - 16), 26)
    draw_badge(
        screen,
        drawer,
        badge_rect,
        f"nimmt: {cards}",
        fill=PALETTE.taken_badge_fill,
        border=PALETTE.taken_badge_border,
        theme=THEME,
    )


def _draw_opponent_slots(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    client_state: ClientState,
    assets: GuiAssets,
    presentation_visuals: PresentationVisuals,
    animation_clock: AnimationClock,
) -> None:
    revealed_by_player = _revealed_card_values_by_player(client_state)
    opponents = _opponent_slot_data(client_state, geometry)

    for index, slot in enumerate(opponents):
        color = _player_color(index)
        circle_rect = slot.geometry.circle_rect
        active_player = slot.player_id == presentation_visuals.active_player_id
        pygame.draw.ellipse(screen, color, circle_rect)
        pygame.draw.ellipse(screen, pygame.Color(255, 255, 255, 150), circle_rect, 2)
        if active_player:
            inflate = 8 + animation_clock.pulse_inflate(period_frames=54, max_pixels=8)
            ring_color = animation_clock.pulsed_color(
                PALETTE.accent,
                PALETTE.accent_hover,
                period_frames=54,
            )
            pygame.draw.ellipse(screen, ring_color, circle_rect.inflate(inflate, inflate), 3)

        initials = _initials(slot.player_name)
        drawer.draw_text(
            screen,
            initials,
            (circle_rect.centerx - 8, circle_rect.centery - 8),
            role="tiny",
            color=PALETTE.text_primary,
        )

        card_value = presentation_visuals.card_value_for_player(slot.player_id)
        if card_value is None:
            card_value = revealed_by_player.get(slot.player_id)
        staged_rect = slot.geometry.staged_card.rect
        if card_value is None:
            draw_card_back(screen, staged_rect)
        else:
            GuiCard.from_card_value(card_value, staged_rect, selected=active_player).draw(
                screen, drawer=drawer, assets=assets
            )


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
    presentation_visuals: PresentationVisuals,
) -> None:
    player_state = client_state.player_state
    if player_state is None:
        return

    target_by_value = {target.card_value: target for target in game_targets.card_targets}
    for card in player_state.hand:
        target = target_by_value.get(card.value)
        if target is None:
            continue
        selected = card.value in presentation_visuals.focus_card_values
        visible_card = GuiCard.from_card(
            card,
            target.rect,
            selected=target.card.selected or selected,
            hovered=target.card.hovered,
        )
        visible_card.draw(screen, drawer=drawer, assets=assets)

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
            color=PALETTE.accent,
        )


def _draw_presentation_card_motion(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    client_state: ClientState,
    game_targets: GameScreenTargets,
    presentation_visuals: PresentationVisuals,
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    if not presentation_visuals.has_event:
        return
    if presentation_visuals.active_row_id is None:
        return
    if not presentation_visuals.focus_card_values:
        return

    card_value = presentation_visuals.replacement_card_value or presentation_visuals.focus_card_values[0]
    source_rect = _presentation_motion_source_rect(
        geometry,
        client_state,
        game_targets,
        presentation_visuals,
        card_value=card_value,
    )
    target_rect = _presentation_motion_target_rect(geometry, client_state, presentation_visuals)
    if source_rect is None or target_rect is None:
        return

    progress = animation_clock.ease_out_cubic(duration_frames=32)
    current_rect = lerp_rect(source_rect, target_rect, progress)
    shadow_rect = current_rect.inflate(12, 12).move(4, 5)
    shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shadow, pygame.Color(0, 0, 0, 80), shadow.get_rect(), border_radius=THEME.spacing.card_radius + 4)
    screen.blit(shadow, shadow_rect)

    path_color = pygame.Color(PALETTE.accent_hover)
    path_color.a = max(35, 120 - round(progress * 70))
    _draw_motion_path(screen, source_rect.center, target_rect.center, path_color)

    GuiCard.from_card_value(card_value, current_rect, selected=True).draw(screen, drawer=drawer, assets=assets)


def _presentation_motion_source_rect(
    geometry: BoardGeometry,
    client_state: ClientState,
    game_targets: GameScreenTargets,
    presentation_visuals: PresentationVisuals,
    *,
    card_value: int,
) -> pygame.Rect | None:
    if presentation_visuals.active_player_id == client_state.own_player_id:
        for target in game_targets.card_targets:
            if target.card_value == card_value:
                return target.rect
        fallback = pygame.Rect(0, 0, *geometry.staged_card_size)
        fallback.center = geometry.hand_rect.center
        return fallback

    for slot in _opponent_slot_data(client_state, geometry):
        if slot.player_id == presentation_visuals.active_player_id:
            return slot.geometry.staged_card.rect

    return None


def _presentation_motion_target_rect(
    geometry: BoardGeometry,
    client_state: ClientState,
    presentation_visuals: PresentationVisuals,
) -> pygame.Rect | None:
    public_state = client_state.public_state
    if public_state is None or presentation_visuals.active_row_id is None:
        return None

    for row_index, row in enumerate(public_state.rows):
        if row.row_id != presentation_visuals.active_row_id:
            continue

        placements = row_card_placements(
            geometry,
            row_index=row_index,
            card_count=max(1, len(row.cards)),
        )
        if placements:
            return placements[-1].rect

        target = pygame.Rect(0, 0, *geometry.row_card_size)
        target.center = geometry.row_columns[row_index].center
        return target

    return None


def _draw_motion_path(
    screen: pygame.Surface,
    start: tuple[int, int],
    end: tuple[int, int],
    color: pygame.Color,
) -> None:
    left = min(start[0], end[0])
    top = min(start[1], end[1])
    width = max(1, abs(end[0] - start[0]))
    height = max(1, abs(end[1] - start[1]))
    surface = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
    local_start = (start[0] - left + 4, start[1] - top + 4)
    local_end = (end[0] - left + 4, end[1] - top + 4)
    pygame.draw.line(surface, color, local_start, local_end, width=2)
    screen.blit(surface, (left - 4, top - 4))


def _draw_stats_field(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    client_state: ClientState,
) -> None:
    rect = geometry.stats_rect
    draw_overlay_panel(screen, rect, radius=12, alpha=35, theme=THEME)

    player_state = client_state.player_state
    public_state = client_state.public_state
    own_score = "-"
    own_name = "-"
    if player_state is not None:
        own_player = player_state.self_player()
        own_score = str(own_player.score)
        own_name = own_player.name

    drawer.draw_text(screen, own_name, (rect.left + 12, rect.top + 14), role="small", color=PALETTE.text_muted)
    drawer.draw_text(screen, "Hornochsen", (rect.left + 12, rect.top + 42), role="small", color=PALETTE.text_muted)
    drawer.draw_text(screen, own_score, (rect.left + 12, rect.top + 66), role="title", color=PALETTE.accent)

    if public_state is not None:
        y = rect.top + 112
        for player in public_state.players:
            marker = "★ " if player.player_id == client_state.own_player_id else ""
            drawer.draw_text(
                screen,
                f"{marker}{player.name}: {player.score}",
                (rect.left + 12, y),
                role="tiny",
                color=PALETTE.text_primary if marker else PALETTE.text_muted,
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
    presentation_visuals: PresentationVisuals,
    assets: GuiAssets,
    animation_clock: AnimationClock,
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
        color=PALETTE.text_muted,
    )

    if presentation_visuals.has_event:
        _draw_presentation_panel(screen, drawer, geometry, presentation_visuals, assets, animation_clock)

    if game_targets.continue_target is not None:
        draw_button(
            screen,
            drawer,
            game_targets.continue_target.rect,
            "Weiter [Leertaste]",
            variant="primary",
            hovered=game_targets.continue_target.hovered,
            theme=THEME,
        )


def _draw_presentation_panel(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    presentation_visuals: PresentationVisuals,
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    events_rect = pygame.Rect(
        geometry.stats_rect.left,
        geometry.stats_rect.bottom - 174,
        geometry.stats_rect.width,
        128,
    )
    _draw_overlay_box(screen, events_rect)
    _draw_presentation_accent(screen, events_rect, animation_clock)

    drawer.draw_text(
        screen,
        presentation_visuals.headline,
        (events_rect.left + 12, events_rect.top + 10),
        role="small",
        color=animation_clock.pulsed_color(PALETTE.accent, PALETTE.accent_hover, period_frames=72),
    )

    if presentation_visuals.focus_card_values:
        _draw_presentation_card_strip(
            screen,
            drawer,
            events_rect,
            card_values=presentation_visuals.focus_card_values,
            assets=assets,
        )
        text_top = events_rect.top + 74
    else:
        text_top = events_rect.top + 34

    lines = list(presentation_visuals.details[:2])
    if lines:
        text_rect = pygame.Rect(events_rect.left + 12, text_top, events_rect.width - 24, events_rect.bottom - text_top - 6)
        drawer.draw_wrapped_lines(screen, lines, text_rect, role="tiny", color=PALETTE.text_primary)


def _draw_presentation_accent(
    screen: pygame.Surface,
    rect: pygame.Rect,
    animation_clock: AnimationClock,
) -> None:
    accent_rect = pygame.Rect(rect.left + 10, rect.top + 7, 4, rect.height - 14)
    accent_color = animation_clock.pulsed_color(
        PALETTE.accent,
        PALETTE.accent_hover,
        period_frames=72,
    )
    accent_color.a = animation_clock.pulse_alpha(period_frames=72, low=120, high=235)
    accent_surface = pygame.Surface(accent_rect.size, pygame.SRCALPHA)
    pygame.draw.rect(accent_surface, accent_color, accent_surface.get_rect(), border_radius=3)
    screen.blit(accent_surface, accent_rect)


def _draw_pulsing_outline(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: pygame.Color,
    animation_clock: AnimationClock,
    *,
    max_inflate: int,
) -> None:
    inflate = animation_clock.pulse_inflate(period_frames=54, max_pixels=max_inflate)
    glow_rect = rect.inflate(inflate, inflate)
    alpha = animation_clock.pulse_alpha(period_frames=54, low=42, high=115)
    overlay = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
    glow_color = pygame.Color(color)
    glow_color.a = alpha
    pygame.draw.rect(overlay, glow_color, overlay.get_rect(), width=3, border_radius=10)
    screen.blit(overlay, glow_rect)


def _draw_presentation_card_strip(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    card_values: tuple[int, ...],
    assets: GuiAssets,
) -> None:
    max_cards = min(4, len(card_values))
    card_width = max(32, min(44, (rect.width - 28) // max(1, max_cards)))
    card_size = (card_width, round(card_width * 1.5))
    x = rect.left + 12
    y = rect.top + 34
    for value in card_values[:max_cards]:
        card_rect = pygame.Rect(x, y, card_size[0], card_size[1])
        GuiCard.from_card_value(value, card_rect, selected=True).draw(screen, drawer=drawer, assets=assets)
        x += card_width + 8

    remaining = len(card_values) - max_cards
    if remaining > 0:
        drawer.draw_text(screen, f"+{remaining}", (x + 2, y + 18), role="small", color=PALETTE.text_muted)


def _draw_overlay_box(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_overlay_panel(screen, rect, theme=THEME)


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
