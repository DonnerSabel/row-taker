"""Laufzeit-Hülle für pygame-GUI-Clients.

Dieses Modul gehört bewusst zur Infrastruktur. Es verbindet Transport,
GameClientCore und einen kleinen Hintergrund-Receive-Loop. Für eigene
GUI-Experimente der Schüler ist es normalerweise nicht der erste Ort für
Änderungen.
"""

from __future__ import annotations

import logging
import queue
import threading

from row_taker.client.actions import ClientAction, ClientActionLeaveSession
from row_taker.client.game_client_core import GameClientCore
from row_taker.client.state import (
    ClientState,
    UiMessage,
    initial_client_state,
    set_flash_message,
)
from row_taker.client.update import CoreUpdate
from row_taker.protocol.errors import ConnectionClosed, TransportError
from row_taker.protocol.messages import JoinLobby, ServerToClientMessage
from row_taker.protocol.transport import ClientTransport

logger = logging.getLogger(__name__)


class LiveGuiClient:
    """Infrastruktur-Baustein zwischen GUI, Transport und ClientCore.

    Die GUI spricht mit dieser Klasse nur über wenige Operationen:
    start(), poll(), apply_local_state(), apply_action() und close().
    Dadurch kann der Rest der GUI den Netzwerkteil weitgehend als
    Black Box behandeln.
    """

    def __init__(
        self,
        transport: ClientTransport,
        *,
        display_name: str,
        own_client_id: str | None = None,
    ) -> None:
        self.transport = transport
        self.display_name = display_name
        self.core = GameClientCore(initial_client_state(own_client_id))
        self._incoming: queue.Queue[ServerToClientMessage | BaseException] = queue.Queue()
        self._receiver_thread: threading.Thread | None = None
        self._closed = False

    @property
    def state(self) -> ClientState:
        return self.core.state

    def start(self) -> None:
        self.transport.send(
            JoinLobby(
                display_name=self.display_name,
                requested_client_id=self.core.state.own_client_id,
            )
        )
        self._receiver_thread = threading.Thread(
            target=self._receive_loop,
            name="row_taker_gui_receive",
            daemon=True,
        )
        self._receiver_thread.start()

    def poll(self) -> None:
        while True:
            try:
                item = self._incoming.get_nowait()
            except queue.Empty:
                break

            if isinstance(item, ConnectionClosed):
                message = "Die Verbindung zum Server wurde beendet."
            elif isinstance(item, TransportError):
                message = f"Netzwerkfehler: {item}"
            elif isinstance(item, BaseException):
                message = "Unerwarteter Netzwerkfehler. Details stehen im Log."
            else:
                self._apply_update(self.core.on_server_message(item))
                continue

            self._apply_update(self.core.on_transport_closed(message))

    def apply_local_state(self, state: ClientState) -> None:
        self.core.state = state

    def apply_action(self, action: ClientAction) -> str:
        update = self.core.on_ui_action(action)
        self._apply_update(update)
        return f"GUI-Aktion erzeugt: {action!r}"

    def close(self, *, send_leave_session: bool) -> None:
        if self._closed:
            return

        if send_leave_session:
            try:
                self.apply_action(ClientActionLeaveSession())
            except TransportError as exc:
                logger.info("LeaveSession could not be sent during shutdown: %s", exc)
            except Exception:
                logger.exception("unexpected error while sending LeaveSession")

        self._closed = True
        self.transport.close()

        if self._receiver_thread is not None:
            self._receiver_thread.join(timeout=0.5)

    def _receive_loop(self) -> None:
        while not self._closed:
            try:
                message = self.transport.receive()
            except ConnectionClosed as exc:
                self._incoming.put(exc)
                return
            except TransportError as exc:
                self._incoming.put(exc)
                return
            except Exception as exc:
                logger.exception("unexpected error in GUI receive loop")
                self._incoming.put(exc)
                return
            self._incoming.put(message)

    def _apply_update(self, update: CoreUpdate) -> None:
        self.core.state = update.state

        for outbound in update.outbound_messages:
            try:
                self.transport.send(outbound)
            except TransportError as exc:
                logger.info("sending to server failed: %s", exc)
                self._set_error_message("Senden an den Server fehlgeschlagen.")
                return
            except Exception:
                logger.exception("unexpected error while sending to server")
                self._set_error_message("Unerwarteter Fehler beim Senden. Details stehen im Log.")
                return

        if update.local_messages:
            self._set_error_message(update.local_messages[-1])

    def _set_error_message(self, text: str) -> None:
        self.core.state = set_flash_message(
            self.core.state,
            UiMessage(level="error", text=text),
        )
