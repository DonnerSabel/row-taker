from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from row_taker.client.state import ClientState
from row_taker.engine.game import Phase
from row_taker.engine.game.models import PlayerID
from row_taker.gui.animation import AnimationClock
from row_taker.gui.assets import DEFAULT_GUI_ASSETS, GuiAssets
from row_taker.gui.board_layout import (
    BoardGeometry,
    CardPlacement,
    OpponentSlotGeometry,
    compute_board_geometry,
    row_card_placements,
)
from row_taker.gui.card import GuiCard, draw_card_back
from row_taker.gui.game_interaction import (
    GameScreenTargets,
    build_game_screen_targets,
    handle_game_event,
)
from row_taker.gui.presentation_renderer import draw_presentation_card_motion, draw_presentation_panel
from row_taker.gui.presentation_visuals import PresentationVisuals, build_presentation_visuals
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_badge, draw_button, draw_overlay_panel
from row_taker.gui_common.layout import DemoLayout
from row_taker.gui_common.primitives import PrimitiveDrawer
from row_taker.gui_common.ui.screen_result import ScreenResult

THEME = DEFAULT_THEME
PALETTE = THEME.palette


@dataclass(frozen=True, slots=True)
class OpponentSlot:
    player_id: PlayerID
    player_name: str
    geometry: OpponentSlotGeometry


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
    draw_presentation_card_motion(
        screen,
        drawer,
        geometry,
        client_state,
        game_targets,
        presentation_visuals,
        assets,
        presentation_clock,
        opponent_slots=_opponent_slot_data(client_state, geometry),
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
        draw_presentation_panel(screen, drawer, geometry, presentation_visuals, assets, animation_clock)

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
