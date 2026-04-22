from __future__ import annotations

import pygame

from row_taker.client.actions import ClientAction
from row_taker.client.state import ClientState
from row_taker.gui_demo.layout import MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH, compute_layout
from row_taker.gui_demo.live_client import LiveGuiClient
from row_taker.gui_demo.primitives import PrimitiveDrawer
from row_taker.gui_demo.screens.connect_screen import (
    ConnectFormState,
    ConnectScreenTargets,
    build_connect_screen_targets,
    handle_connect_event,
    normalized_connection_values,
    render_connect_screen,
)
from row_taker.gui_demo.screens.game_screen import (
    GameScreenTargets,
    build_game_screen_targets,
    handle_game_event,
    render_game_screen,
)
from row_taker.gui_demo.screens.lobby_screen import (
    LobbyScreenTargets,
    build_lobby_screen_targets,
    handle_lobby_event,
    render_lobby_screen,
)
from row_taker.protocol.transport import ClientTransport

WINDOW_TITLE = 'Row-Taker GUI Demo'
FPS = 30


class GuiDemoApp:
    def __init__(self) -> None:
        self._running = True
        self._frame_count = 0
        self._screen: pygame.Surface | None = None
        self._clock: pygame.time.Clock | None = None
        self._drawer: PrimitiveDrawer | None = None
        self._last_action_summary = 'Noch keine GUI-Aktion.'
        self._live_client: LiveGuiClient | None = None
        self._client_state: ClientState | None = None
        self._connect_form = ConnectFormState()
        self._connect_targets: ConnectScreenTargets | None = None
        self._lobby_targets: LobbyScreenTargets | None = None
        self._game_targets: GameScreenTargets | None = None

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
            if self._live_client is None:
                mapped = handle_connect_event(
                    event,
                    connect_form=self._connect_form,
                    connect_targets=self._connect_targets,
                )
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    mapped = mapped if mapped.request_quit else type(mapped)(request_quit=True)
            elif self._client_state is not None and self._client_state.client_mode.value == 'lobby':
                mapped = handle_lobby_event(
                    event,
                    state=self._client_state,
                    lobby_targets=self._lobby_targets,
                )
            else:
                mapped = handle_game_event(
                    event,
                    state=self._client_state,
                    game_targets=self._game_targets,
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
                self._last_action_summary = 'Updated local GUI navigation state.'
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
                error_message='Bitte gültige Werte für Server IP, Port und Display name eingeben.',
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
                active_field='host',
                error_message=f'Verbindung fehlgeschlagen: {exc}',
                status_message='Bitte Werte prüfen und erneut verbinden.',
            )
            return

        self._live_client = live_client
        self._client_state = live_client.state
        self._last_action_summary = f'Connected to {host}:{port} as {display_name}.'
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
            raise RuntimeError('GuiDemoApp not initialized')

        layout = compute_layout(*self._screen.get_size())
        if self._live_client is None:
            self._connect_targets = build_connect_screen_targets(layout)
            if self._connect_targets is None:
                raise RuntimeError('Connect screen targets missing')
            render_connect_screen(
                self._screen,
                drawer=self._drawer,
                layout=layout,
                connect_form=self._connect_form,
                connect_targets=self._connect_targets,
            )
        else:
            if self._client_state is None:
                raise RuntimeError('Live client active without client state')
            if self._client_state.client_mode.value == 'lobby':
                self._lobby_targets = build_lobby_screen_targets(layout, self._client_state)
                render_lobby_screen(
                    self._screen,
                    drawer=self._drawer,
                    layout=layout,
                    client_state=self._client_state,
                    frame_count=self._frame_count,
                    lobby_targets=self._lobby_targets,
                    last_action_summary=self._last_action_summary,
                )
            else:
                self._game_targets = build_game_screen_targets(layout, self._client_state)
                render_game_screen(
                    self._screen,
                    drawer=self._drawer,
                    layout=layout,
                    client_state=self._client_state,
                    frame_count=self._frame_count,
                    game_targets=self._game_targets,
                    last_action_summary=self._last_action_summary,
                )
        pygame.display.flip()

    def _tick(self) -> None:
        if self._clock is None:
            raise RuntimeError('GuiDemoApp not initialized')
        self._clock.tick(FPS)
        self._frame_count += 1

    def _refresh_targets(self) -> None:
        if self._screen is None:
            return
        layout = compute_layout(*self._screen.get_size())
        if self._live_client is None:
            self._connect_targets = build_connect_screen_targets(layout)
            self._lobby_targets = None
            self._game_targets = None
            return
        if self._client_state is None:
            self._lobby_targets = None
            self._game_targets = None
            return
        if self._client_state.client_mode.value == 'lobby':
            self._lobby_targets = build_lobby_screen_targets(layout, self._client_state)
            self._game_targets = None
        else:
            self._game_targets = build_game_screen_targets(layout, self._client_state)
            self._lobby_targets = None
