from __future__ import annotations

import pygame

from row_taker.client.actions import ClientAction
from row_taker.client.state import ClientState
from row_taker.gui_demo.demo_local_reducer import apply_demo_action
from row_taker.gui_demo.demo_state import build_demo_states
from row_taker.gui_demo.input_mapping import map_pygame_event
from row_taker.gui_demo.interactions import InteractionMap, build_interaction_map
from row_taker.gui_demo.layout import MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, compute_layout
from row_taker.gui_demo.live_client import LiveGuiClient
from row_taker.gui_demo.primitives import PrimitiveDrawer
from row_taker.gui_demo.render import render_app

WINDOW_TITLE = "Row-Taker GUI Demo"
FPS = 30
DEFAULT_DEMO_SCENE = "lobby"


class GuiDemoApp:
    def __init__(
        self,
        *,
        initial_state: ClientState | None = None,
        live_client: LiveGuiClient | None = None,
    ) -> None:
        self._running = True
        self._frame_count = 0
        self._screen: pygame.Surface | None = None
        self._clock: pygame.time.Clock | None = None
        self._drawer: PrimitiveDrawer | None = None
        self._demo_states: dict[str, ClientState] = {}
        self._active_demo_scene: str | None = None
        self._interaction_map = InteractionMap()
        self._last_action_summary = "No GUI action yet."
        self._live_client = live_client

        if live_client is not None:
            self._client_state = live_client.state
        elif initial_state is None:
            self._demo_states = build_demo_states()
            self._active_demo_scene = DEFAULT_DEMO_SCENE
            self._client_state = self._demo_states[DEFAULT_DEMO_SCENE]
        else:
            self._client_state = initial_state

    def run(self) -> int:
        pygame.init()
        try:
            pygame.display.set_caption(WINDOW_TITLE)
            self._screen = pygame.display.set_mode(
                (MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT),
                pygame.RESIZABLE,
            )
            self._clock = pygame.time.Clock()
            self._drawer = PrimitiveDrawer()

            if self._live_client is not None:
                self._live_client.start()
                self._client_state = self._live_client.state
                self._last_action_summary = "Live mode active."

            self._refresh_interaction_map()

            while self._running:
                self._poll_live_client()
                self._handle_events()
                self._render_frame()
                self._tick()

            return 0
        finally:
            if self._live_client is not None:
                self._live_client.close(send_leave_session=not self._client_state.should_exit)
            pygame.quit()

    def _poll_live_client(self) -> None:
        if self._live_client is None:
            return
        self._live_client.poll()
        self._client_state = self._live_client.state
        self._refresh_interaction_map()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            mapped = map_pygame_event(
                event,
                state=self._client_state,
                interaction_map=self._interaction_map,
            )
            if mapped.request_quit:
                self._running = False
                continue

            if mapped.demo_scene_name is not None and self._live_client is None and mapped.demo_scene_name in self._demo_states:
                self._active_demo_scene = mapped.demo_scene_name
                self._client_state = self._demo_states[mapped.demo_scene_name]
                self._last_action_summary = f"Switched to demo scene '{mapped.demo_scene_name}'."
                self._refresh_interaction_map()
                continue

            if mapped.next_state is not None:
                self._apply_local_state(mapped.next_state)
                self._last_action_summary = "Updated local GUI navigation state."
                self._refresh_interaction_map()
                continue

            if mapped.client_action is not None:
                self._apply_client_action(mapped.client_action)
                self._refresh_interaction_map()

    def _apply_local_state(self, next_state: ClientState) -> None:
        self._client_state = next_state
        if self._live_client is not None:
            self._live_client.apply_local_state(next_state)
        elif self._active_demo_scene is not None:
            self._demo_states[self._active_demo_scene] = next_state

    def _apply_client_action(self, action: ClientAction) -> None:
        if self._live_client is not None:
            self._last_action_summary = self._live_client.apply_action(action)
            self._client_state = self._live_client.state
            return

        self._last_action_summary = _format_action(action)
        self._client_state, next_scene = apply_demo_action(self._client_state, action)
        if next_scene is not None and next_scene in self._demo_states:
            self._active_demo_scene = next_scene
            self._demo_states[next_scene] = self._client_state
        elif self._active_demo_scene is not None:
            self._demo_states[self._active_demo_scene] = self._client_state

    def _render_frame(self) -> None:
        if self._screen is None or self._drawer is None:
            raise RuntimeError("GuiDemoApp not initialized")

        layout = compute_layout(*self._screen.get_size())
        self._interaction_map = build_interaction_map(layout, self._client_state)
        render_app(
            self._screen,
            drawer=self._drawer,
            layout=layout,
            client_state=self._client_state,
            frame_count=self._frame_count,
            active_demo_scene=self._active_demo_scene,
            interaction_map=self._interaction_map,
            last_action_summary=self._last_action_summary,
        )
        pygame.display.flip()

    def _tick(self) -> None:
        if self._clock is None:
            raise RuntimeError("GuiDemoApp not initialized")
        self._clock.tick(FPS)
        self._frame_count += 1

    def _refresh_interaction_map(self) -> None:
        if self._screen is None:
            return
        layout = compute_layout(*self._screen.get_size())
        self._interaction_map = build_interaction_map(layout, self._client_state)


def _format_action(action: object) -> str:
    return f"GUI produced {action!r}"


def run() -> int:
    return GuiDemoApp().run()
