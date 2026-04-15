from __future__ import annotations

import pygame

from row_taker.client.actions import ClientAction
from row_taker.client.state import ClientState
from row_taker.gui_demo.connect_screen import (
    ConnectFormState,
    build_connect_screen_targets,
    normalized_connection_values,
)
from row_taker.gui_demo.input_mapping import map_pygame_event
from row_taker.gui_demo.interactions import InteractionMap, build_session_interaction_map
from row_taker.gui_demo.layout import MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, compute_layout
from row_taker.gui_demo.live_client import LiveGuiClient
from row_taker.gui_demo.primitives import PrimitiveDrawer
from row_taker.gui_demo.render import render_connect_screen, render_session
from row_taker.protocol.transport import ClientTransport

WINDOW_TITLE = "Row-Taker GUI Demo"
FPS = 30


class GuiDemoApp:
    def __init__(self) -> None:
        self._running = True
        self._frame_count = 0
        self._screen: pygame.Surface | None = None
        self._clock: pygame.time.Clock | None = None
        self._drawer: PrimitiveDrawer | None = None
        self._interaction_map = InteractionMap()
        self._last_action_summary = "Noch keine GUI-Aktion."
        self._live_client: LiveGuiClient | None = None
        self._client_state: ClientState | None = None
        self._connect_form = ConnectFormState()
        self._connect_targets = None

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
            self._refresh_targets()

            while self._running:
                self._poll_live_client()
                self._handle_events()
                self._render_frame()
                self._tick()

            return 0
        finally:
            if self._live_client is not None:
                send_leave = self._client_state is not None and not self._client_state.should_exit
                self._live_client.close(send_leave_session=send_leave)
            pygame.quit()

    def _poll_live_client(self) -> None:
        if self._live_client is None:
            return
        self._live_client.poll()
        self._client_state = self._live_client.state
        self._refresh_targets()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            mapped = map_pygame_event(
                event,
                state=self._client_state,
                interaction_map=self._interaction_map if self._live_client is not None else None,
                connect_form=self._connect_form if self._live_client is None else None,
                connect_targets=self._connect_targets if self._live_client is None else None,
            )

            if mapped.request_quit:
                self._running = False
                continue

            if mapped.next_connect_form is not None:
                self._connect_form = mapped.next_connect_form
                self._refresh_targets()
                continue

            if mapped.connect_requested:
                self._attempt_connect()
                self._refresh_targets()
                continue

            if mapped.next_state is not None:
                self._apply_local_state(mapped.next_state)
                self._last_action_summary = "Updated local GUI navigation state."
                self._refresh_targets()
                continue

            if mapped.client_action is not None:
                self._apply_client_action(mapped.client_action)
                self._refresh_targets()

    def _attempt_connect(self) -> None:
        connection_values = normalized_connection_values(self._connect_form)
        if connection_values is None:
            self._connect_form = ConnectFormState(
                host=self._connect_form.host,
                port=self._connect_form.port,
                display_name=self._connect_form.display_name,
                active_field=self._connect_form.active_field,
                error_message="Bitte gültige Werte für Server IP, Port und Display name eingeben.",
                status_message=self._connect_form.status_message,
            )
            return

        host, port, display_name = connection_values
        try:
            transport = ClientTransport.connect(host, port)
            live_client = LiveGuiClient(transport, display_name=display_name)
            live_client.start()
        except Exception as exc:
            self._connect_form = ConnectFormState(
                host=host,
                port=str(port),
                display_name=display_name,
                active_field="host",
                error_message=f"Verbindung fehlgeschlagen: {exc}",
                status_message="Bitte Werte prüfen und erneut verbinden.",
            )
            return

        self._live_client = live_client
        self._client_state = live_client.state
        self._last_action_summary = f"Connected to {host}:{port} as {display_name}."
        self._refresh_targets()

    def _apply_local_state(self, next_state: ClientState) -> None:
        self._client_state = next_state
        if self._live_client is not None:
            self._live_client.apply_local_state(next_state)

    def _apply_client_action(self, action: ClientAction) -> None:
        if self._live_client is None:
            return
        self._last_action_summary = self._live_client.apply_action(action)
        self._client_state = self._live_client.state

    def _render_frame(self) -> None:
        if self._screen is None or self._drawer is None:
            raise RuntimeError("GuiDemoApp not initialized")

        layout = compute_layout(*self._screen.get_size())
        if self._live_client is None:
            self._connect_targets = build_connect_screen_targets(layout)
            render_connect_screen(
                self._screen,
                drawer=self._drawer,
                layout=layout,
                connect_form=self._connect_form,
                connect_targets=self._connect_targets,
            )
        else:
            if self._client_state is None:
                raise RuntimeError("Live client active without client state")
            self._interaction_map = build_session_interaction_map(layout, self._client_state)
            render_session(
                self._screen,
                drawer=self._drawer,
                layout=layout,
                client_state=self._client_state,
                frame_count=self._frame_count,
                interaction_map=self._interaction_map,
                last_action_summary=self._last_action_summary,
            )
        pygame.display.flip()

    def _tick(self) -> None:
        if self._clock is None:
            raise RuntimeError("GuiDemoApp not initialized")
        self._clock.tick(FPS)
        self._frame_count += 1

    def _refresh_targets(self) -> None:
        if self._screen is None:
            return
        layout = compute_layout(*self._screen.get_size())
        if self._live_client is None:
            self._connect_targets = build_connect_screen_targets(layout)
            self._interaction_map = InteractionMap()
        elif self._client_state is not None:
            self._interaction_map = build_session_interaction_map(layout, self._client_state)
