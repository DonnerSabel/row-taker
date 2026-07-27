from __future__ import annotations

import pygame

from row_taker.client.actions import ClientAction
from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.state import ClientState
from row_taker.gui.screens.connect_screen import ConnectScreen
from row_taker.gui.screens.game_screen import GameFrame
from row_taker.gui.screens.lobby_screen import LobbyScreen
from row_taker.gui.layout import (
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    GuiLayout,
    compute_layout,
)
from row_taker.gui.live_client import LiveGuiClient
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.connect_form_state import ConnectFormState
from row_taker.gui.screen_result import ScreenResult
from row_taker.protocol.transport import ClientTransport

WINDOW_TITLE = "Row-Taker"
FPS = 30


class GuiApp:
    """Graphical Row-Taker client.

    GUI screens delegate client semantics to ``LiveGuiClient`` and render game
    states exclusively through the production ``GameVisualState`` path.
    """

    def __init__(self) -> None:
        self._running = True
        self._frame_count = 0
        self._screen: pygame.Surface | None = None
        self._clock: pygame.time.Clock | None = None
        self._drawer: PrimitiveDrawer | None = None
        self._last_action_summary = "Noch keine GUI-Aktion."
        self._live_client: LiveGuiClient | None = None
        self._client_state: ClientState | None = None
        self._presentation_step: PresentationStep | None = None
        self._presentation_start_frame = 0
        self._connect_form = ConnectFormState()

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
                self._poll_live_client()
                self._process_current_screen()
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
        self._sync_presentation_clock()

    def _process_current_screen(self) -> None:
        if self._screen is None or self._drawer is None:
            raise RuntimeError("GuiApp not initialized")

        layout = self._current_layout()
        current_screen = self._build_current_screen(layout)
        targets = current_screen.build_targets(layout)

        for event in pygame.event.get():
            result = current_screen.handle_event(event, targets)
            self._apply_screen_result(result)
            if not self._running:
                return

            layout = self._current_layout()
            current_screen = self._build_current_screen(layout)
            targets = current_screen.build_targets(layout)

        current_screen.render(
            self._screen,
            drawer=self._drawer,
            layout=layout,
            targets=targets,
        )
        pygame.display.flip()

    def _build_current_screen(
        self,
        layout: GuiLayout,
    ) -> ConnectScreen | LobbyScreen | GameFrame:
        if self._live_client is None:
            return ConnectScreen(connect_form=self._connect_form)

        if self._client_state is None:
            raise RuntimeError("Live client active without client state")

        if self._client_state.client_mode.value == "lobby":
            return LobbyScreen(
                state=self._client_state,
                frame_count=self._frame_count,
                last_action_summary=self._last_action_summary,
            )

        return GameFrame.from_layout(
            layout=layout,
            state=self._client_state,
            frame_count=self._frame_count,
            presentation_frame_count=max(
                0,
                self._frame_count - self._presentation_start_frame,
            ),
            last_action_summary=self._last_action_summary,
        )

    def _apply_screen_result(self, result: ScreenResult) -> None:
        if result.request_quit:
            self._running = False
            return

        if result.next_connect_form is not None:
            self._connect_form = result.next_connect_form
            return

        if result.connect_requested:
            self._attempt_connect()
            return

        if result.next_state is not None:
            self._apply_local_state(result.next_state)
            self._last_action_summary = "Lokale GUI-Navigation aktualisiert."
            return

        if result.client_action is not None:
            self._apply_client_action(result.client_action)

    def _attempt_connect(self) -> None:
        current_screen = self._build_current_screen(self._current_layout())
        connection_values = current_screen.normalized_connection_values()
        if connection_values is None:
            self._connect_form = ConnectFormState(
                host=self._connect_form.host,
                port=self._connect_form.port,
                display_name=self._connect_form.display_name,
                active_field=self._connect_form.active_field,
                error_message="Bitte gültige Werte für Server IP, Port und Anzeigename eingeben.",
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
        self._last_action_summary = f"Verbunden mit {host}:{port} als {display_name}."

    def _apply_local_state(self, next_state: ClientState) -> None:
        self._client_state = next_state
        self._sync_presentation_clock()
        if self._live_client is not None:
            self._live_client.apply_local_state(next_state)

    def _apply_client_action(self, action: ClientAction) -> None:
        if self._live_client is None:
            return
        self._last_action_summary = self._live_client.apply_action(action)
        self._client_state = self._live_client.state
        self._sync_presentation_clock()

    def _sync_presentation_clock(self) -> None:
        step = (
            None
            if self._client_state is None
            else self._client_state.current_presentation_step
        )
        if step is self._presentation_step:
            return
        self._presentation_step = step
        self._presentation_start_frame = self._frame_count

    def _current_layout(self):
        if self._screen is None:
            raise RuntimeError("GuiApp not initialized")
        return compute_layout(*self._screen.get_size())

    def _tick(self) -> None:
        if self._clock is None:
            raise RuntimeError("GuiApp not initialized")
        self._frame_count += 1
        self._clock.tick(FPS)
