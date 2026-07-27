from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.state import ClientState
from row_taker.engine.game.models import PlayerID
from row_taker.gui.animation import AnimationClock
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
from row_taker.gui.game_interaction import (
    GameScreenTargets,
    build_game_screen_targets,
    handle_game_event,
)
from row_taker.gui.game_visual_builder import build_game_visual_state
from row_taker.gui.game_visual_state import (
    GameVisualState,
    MessageLevel,
    RowEmphasis,
    VisualCard,
)
from row_taker.gui.presentation_renderer import (
    draw_presentation_card_motion,
    draw_presentation_panel,
)
from row_taker.gui.theme import DEFAULT_THEME
from row_taker.gui.widgets import draw_badge, draw_button, draw_overlay_panel
from row_taker.gui.layout import GuiLayout
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.screen_result import ScreenResult

THEME = DEFAULT_THEME
PALETTE = THEME.palette


@dataclass(frozen=True, slots=True)
class OpponentSlot:
    player_id: PlayerID
    player_name: str
    geometry: OpponentSlotGeometry


@dataclass(frozen=True, slots=True)
class GameFrame:
    """One fully prepared production frame of the game screen.

    The client state is translated once at the frame boundary. Geometry,
    targets, rendering, and event handling below that boundary use the same
    immutable ``GameVisualState``.
    """

    visual_state: GameVisualState
    frame_count: int
    presentation_frame_count: int
    geometry: BoardGeometry
    targets: GameScreenTargets

    @classmethod
    def from_layout(
        cls,
        *,
        layout: GuiLayout,
        state: ClientState,
        frame_count: int,
        presentation_frame_count: int,
        last_action_summary: str,
        mouse_pos: tuple[int, int] | None = None,
    ) -> GameFrame:
        visual_state = build_game_visual_state(
            state,
            last_action_summary=last_action_summary,
            presentation_frame_count=presentation_frame_count,
        )
        geometry = _compute_geometry(layout.window_rect, visual_state)
        targets = build_game_screen_targets(
            geometry,
            visual_state,
            mouse_pos=mouse_pos,
        )
        return cls(
            visual_state=visual_state,
            frame_count=frame_count,
            presentation_frame_count=presentation_frame_count,
            geometry=geometry,
            targets=targets,
        )

    def handle_event(self, event: pygame.event.Event) -> ScreenResult:
        """Handle an event against this frame's own prepared targets."""

        return handle_game_event(
            event,
            visual_state=self.visual_state,
            game_targets=self.targets,
        )

    def render(
        self,
        screen: pygame.Surface,
        *,
        drawer: PrimitiveDrawer,
    ) -> None:
        """Render this complete frame through the production game renderer."""

        render_game_screen(
            screen,
            drawer=drawer,
            geometry=self.geometry,
            visual_state=self.visual_state,
            game_targets=self.targets,
            frame_count=self.frame_count,
            presentation_frame_count=self.presentation_frame_count,
        )


def render_game_screen(
    screen: pygame.Surface,
    *,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    frame_count: int,
    presentation_frame_count: int,
    assets: GuiAssets = DEFAULT_GUI_ASSETS,
) -> None:
    del frame_count  # Reserved for stable-frame animation independent of presentation steps.
    presentation_clock = AnimationClock(presentation_frame_count)

    _draw_full_background(screen, geometry.window_rect, assets)
    _draw_rows(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
        assets,
        presentation_clock,
    )
    _draw_opponent_slots(
        screen,
        drawer,
        geometry,
        visual_state,
        assets,
        presentation_clock,
    )
    _draw_hand(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
        assets,
    )
    draw_presentation_card_motion(
        screen,
        drawer,
        geometry,
        visual_state,
        assets,
        opponent_slots=_opponent_slot_data(visual_state, geometry),
    )
    _draw_stats_field(screen, drawer, geometry, visual_state)
    _draw_status_overlay(
        screen,
        drawer,
        geometry,
        visual_state,
        game_targets,
        assets,
        presentation_clock,
    )


def _compute_geometry(
    window_rect: pygame.Rect,
    visual_state: GameVisualState,
) -> BoardGeometry:
    return compute_board_geometry(
        window_rect.size,
        row_count=len(visual_state.rows) or 4,
        hand_card_count=len(visual_state.hand),
        opponent_count=len(visual_state.opponents),
    )


def _draw_full_background(
    screen: pygame.Surface,
    window_rect: pygame.Rect,
    assets: GuiAssets,
) -> None:
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
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    row_target_by_id = {target.row_id: target for target in game_targets.row_targets}

    for row_index, (row, column_rect) in enumerate(
        zip(visual_state.rows, geometry.row_columns, strict=False)
    ):
        target = row_target_by_id.get(row.row_id)
        selectable = row.row_id in visual_state.interaction.selectable_row_ids
        hovered = bool(target.hovered) if target is not None else False
        placements = row_card_placements(
            geometry,
            row_index=row_index,
            card_count=len(row.cards),
        )
        emphasis = row.emphasis
        taken_values = tuple(card.card_value for card in row.taken_cards)
        _draw_row_column(
            screen,
            drawer,
            column_rect,
            row_id=row.row_id,
            cards=row.cards,
            placements=placements,
            selectable=selectable,
            hovered=hovered,
            emphasis=emphasis,
            taken_card_values=taken_values,
            assets=assets,
            animation_clock=animation_clock,
        )


def _draw_row_column(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    *,
    row_id: object,
    cards: tuple[VisualCard, ...],
    placements: tuple[CardPlacement, ...],
    selectable: bool,
    hovered: bool,
    emphasis: RowEmphasis,
    taken_card_values: tuple[int, ...],
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    lane_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    lane_fill = (
        PALETTE.lane_overlay_active
        if emphasis != "none" or hovered
        else PALETTE.lane_overlay
    )
    pygame.draw.rect(lane_surface, lane_fill, lane_surface.get_rect(), border_radius=8)
    screen.blit(lane_surface, rect)

    border = _row_border_color(
        selectable=selectable,
        hovered=hovered,
        emphasis=emphasis,
    )
    if emphasis != "none":
        _draw_pulsing_outline(screen, rect, border, animation_clock, max_inflate=12)
    border_width = 4 if emphasis != "none" or hovered else 3 if selectable else 1
    pygame.draw.rect(screen, border, rect, border_width, border_radius=8)

    label_color = (
        border
        if selectable or hovered or emphasis != "none"
        else PALETTE.text_muted
    )
    drawer.draw_text(
        screen,
        str(row_id),
        (rect.left + 8, rect.top + 6),
        role="small",
        color=label_color,
    )

    if emphasis in {"taken", "overflow"}:
        _draw_row_taken_badge(
            screen,
            drawer,
            rect,
            taken_card_values=taken_card_values,
        )

    for card, placement in zip(cards, placements, strict=False):
        selected = selectable or hovered or emphasis != "none"
        GuiCard(
            card_value=card.card_value,
            bullheads=card.bullheads,
            rect=placement.rect,
            selected=selected,
        ).draw(screen, drawer=drawer, assets=assets)


def _row_border_color(
    *,
    selectable: bool,
    hovered: bool,
    emphasis: RowEmphasis,
) -> pygame.Color:
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
    *,
    taken_card_values: tuple[int, ...],
) -> None:
    cards = ", ".join(str(value) for value in taken_card_values)
    if not cards:
        return

    badge_rect = pygame.Rect(
        rect.left + 8,
        rect.bottom - 34,
        max(1, rect.width - 16),
        26,
    )
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
    visual_state: GameVisualState,
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    opponents = _opponent_slot_data(visual_state, geometry)

    for index, (player, slot) in enumerate(
        zip(visual_state.opponents, opponents, strict=False)
    ):
        color = _player_color(index)
        circle_rect = slot.geometry.circle_rect
        active_player = player.emphasis == "active"
        pygame.draw.ellipse(screen, color, circle_rect)
        pygame.draw.ellipse(
            screen,
            pygame.Color(255, 255, 255, 150),
            circle_rect,
            2,
        )
        if active_player:
            inflate = 8 + animation_clock.pulse_inflate(
                period_frames=54,
                max_pixels=8,
            )
            ring_color = animation_clock.pulsed_color(
                PALETTE.accent,
                PALETTE.accent_hover,
                period_frames=54,
            )
            pygame.draw.ellipse(
                screen,
                ring_color,
                circle_rect.inflate(inflate, inflate),
                3,
            )

        initials = _initials(player.name)
        drawer.draw_text(
            screen,
            initials,
            (circle_rect.centerx - 8, circle_rect.centery - 8),
            role="tiny",
            color=PALETTE.text_primary,
        )

        card_value = player.staged_card_value
        staged_rect = slot.geometry.staged_card.rect
        if card_value is None:
            draw_card_back(screen, staged_rect)
        else:
            GuiCard.from_card_value(
                card_value,
                staged_rect,
                selected=active_player,
            ).draw(screen, drawer=drawer, assets=assets)


def _opponent_slot_data(
    visual_state: GameVisualState,
    geometry: BoardGeometry,
) -> tuple[OpponentSlot, ...]:
    return tuple(
        OpponentSlot(
            player_id=player.player_id,
            player_name=player.name,
            geometry=slot_geometry,
        )
        for player, slot_geometry in zip(
            visual_state.opponents,
            geometry.opponent_slots,
            strict=False,
        )
    )


def _draw_hand(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    assets: GuiAssets,
) -> None:
    hand_cards = visual_state.hand
    placements = hand_card_placements(geometry, card_count=len(hand_cards))
    target_by_value = {target.card_value: target for target in game_targets.card_targets}

    for card, placement in zip(hand_cards, placements, strict=False):
        if not card.visible:
            continue
        target = target_by_value.get(card.card_value)
        selected = card.emphasis == "selected" or (
            target is not None and target.card.selected
        )
        hovered = target.card.hovered if target is not None else False
        GuiCard(
            card_value=card.card_value,
            bullheads=card.bullheads,
            rect=placement.rect,
            selected=selected,
            hovered=hovered,
        ).draw(screen, drawer=drawer, assets=assets)

    if visual_state.status.hand_prompt is not None and placements:
        pending_rect = pygame.Rect(
            24,
            max(60, placements[0].rect.top - 42),
            270,
            34,
        )
        _draw_overlay_box(screen, pending_rect)
        drawer.draw_text(
            screen,
            visual_state.status.hand_prompt,
            (pending_rect.left + 10, pending_rect.top + 8),
            role="small",
            color=PALETTE.accent,
        )


def _draw_stats_field(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
) -> None:
    rect = geometry.stats_rect
    draw_overlay_panel(screen, rect, radius=12, alpha=35, theme=THEME)

    own_player = visual_state.own_player
    own_score = str(own_player.score) if own_player is not None else "-"
    own_name = own_player.name if own_player is not None else "-"

    drawer.draw_text(
        screen,
        own_name,
        (rect.left + 12, rect.top + 14),
        role="small",
        color=PALETTE.text_muted,
    )
    drawer.draw_text(
        screen,
        "Hornochsen",
        (rect.left + 12, rect.top + 42),
        role="small",
        color=PALETTE.text_muted,
    )
    drawer.draw_text(
        screen,
        own_score,
        (rect.left + 12, rect.top + 66),
        role="title",
        color=PALETTE.accent,
    )

    y = rect.top + 112
    for player in visual_state.players:
        marker = "★ " if player.is_self else ""
        drawer.draw_text(
            screen,
            f"{marker}{player.name}: {player.score}",
            (rect.left + 12, y),
            role="tiny",
            color=PALETTE.text_primary if player.is_self else PALETTE.text_muted,
        )
        y += 20
        if y > rect.bottom - 54:
            break


def _draw_status_overlay(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    geometry: BoardGeometry,
    visual_state: GameVisualState,
    game_targets: GameScreenTargets,
    assets: GuiAssets,
    animation_clock: AnimationClock,
) -> None:
    _draw_overlay_box(screen, geometry.overlay_rect)

    drawer.draw_text(
        screen,
        visual_state.status.primary_line,
        (geometry.overlay_rect.left + 10, geometry.overlay_rect.top + 8),
        role="small",
    )
    drawer.draw_text(
        screen,
        visual_state.status.secondary_line,
        (geometry.overlay_rect.left + 10, geometry.overlay_rect.top + 30),
        role="tiny",
        color=_status_message_color(visual_state.status.message_level),
    )

    presentation_panel = visual_state.presentation_panel
    if presentation_panel is not None:
        draw_presentation_panel(
            screen,
            drawer,
            geometry,
            presentation_panel,
            assets,
            animation_clock,
        )

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


def _status_message_color(level: MessageLevel) -> pygame.Color:
    if level == "error":
        return PALETTE.danger
    if level == "info":
        return PALETTE.text_primary
    return PALETTE.text_muted


def _draw_pulsing_outline(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: pygame.Color,
    animation_clock: AnimationClock,
    *,
    max_inflate: int,
) -> None:
    inflate = animation_clock.pulse_inflate(
        period_frames=54,
        max_pixels=max_inflate,
    )
    glow_rect = rect.inflate(inflate, inflate)
    alpha = animation_clock.pulse_alpha(period_frames=54, low=42, high=115)
    overlay = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
    glow_color = pygame.Color(color)
    glow_color.a = alpha
    pygame.draw.rect(
        overlay,
        glow_color,
        overlay.get_rect(),
        width=3,
        border_radius=10,
    )
    screen.blit(overlay, glow_rect)


def _draw_overlay_box(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_overlay_panel(screen, rect, theme=THEME)


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
