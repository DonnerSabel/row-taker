from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.state import ClientState
from row_taker.gui.board_layout import BoardGeometry, compute_board_geometry
from row_taker.gui.game_interaction import (
    GameScreenTargets,
    build_game_screen_targets,
    handle_game_event,
)
from row_taker.gui.game_visual_builder import build_game_visual_state
from row_taker.gui.game_visual_state import GameVisualState
from row_taker.gui.layout import GuiLayout
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.rendering.game_renderer import render_game_screen
from row_taker.gui.screen_result import ScreenResult


@dataclass(frozen=True, slots=True)
class GameFrame:
    """One fully prepared production frame of the game screen.

    The client state is translated once at the frame boundary. Geometry,
    targets, rendering, and event handling below that boundary use the same
    immutable ``GameVisualState``.
    """

    visual_state: GameVisualState
    presentation_elapsed_frames: int
    geometry: BoardGeometry
    targets: GameScreenTargets

    @classmethod
    def from_layout(
        cls,
        *,
        layout: GuiLayout,
        state: ClientState,
        presentation_elapsed_frames: int,
        last_action_summary: str,
        mouse_pos: tuple[int, int] | None = None,
    ) -> GameFrame:
        visual_state = build_game_visual_state(
            state,
            last_action_summary=last_action_summary,
            presentation_elapsed_frames=presentation_elapsed_frames,
        )
        geometry = compute_board_geometry(
            layout.window_rect.size,
            row_count=len(visual_state.rows) or 4,
            hand_card_count=len(visual_state.hand),
            opponent_count=len(visual_state.opponents),
        )
        targets = build_game_screen_targets(
            geometry,
            visual_state,
            mouse_pos=mouse_pos,
        )
        return cls(
            visual_state=visual_state,
            presentation_elapsed_frames=presentation_elapsed_frames,
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
            presentation_elapsed_frames=self.presentation_elapsed_frames,
        )
