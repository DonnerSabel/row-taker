from __future__ import annotations

import pygame

from row_taker.client.state import ClientState, initial_client_state
from row_taker.gui_demo.input_mapping import map_pygame_event
from row_taker.gui_demo.layout import MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, compute_layout
from row_taker.gui_demo.primitives import PrimitiveDrawer
from row_taker.gui_demo.render import render_app

WINDOW_TITLE = "Row-Taker GUI Demo"
FPS = 30


class GuiDemoApp:
    def __init__(self, *, initial_state: ClientState | None = None) -> None:
        self._running = True
        self._client_state = initial_state or initial_client_state()
        self._frame_count = 0
        self._screen: pygame.Surface | None = None
        self._clock: pygame.time.Clock | None = None
        self._drawer: PrimitiveDrawer | None = None

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

            while self._running:
                self._handle_events()
                self._render_frame()
                self._tick()

            return 0
        finally:
            pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            mapped = map_pygame_event(event)
            if mapped.request_quit:
                self._running = False

    def _render_frame(self) -> None:
        if self._screen is None or self._drawer is None:
            raise RuntimeError("GuiDemoApp not initialized")

        layout = compute_layout(*self._screen.get_size())
        render_app(
            self._screen,
            drawer=self._drawer,
            layout=layout,
            client_state=self._client_state,
            frame_count=self._frame_count,
        )
        pygame.display.flip()

    def _tick(self) -> None:
        if self._clock is None:
            raise RuntimeError("GuiDemoApp not initialized")
        self._clock.tick(FPS)
        self._frame_count += 1


def run() -> int:
    return GuiDemoApp().run()
