from __future__ import annotations

import logging
import random
import socket
import threading
from contextlib import suppress
from dataclasses import dataclass, field

from row_taker.protocol.errors import ConnectionClosed, ProtocolError, TransportError
from row_taker.protocol.messages import (
    ClientToServerMessage,
    IdentityAssigned,
    JoinLobby,
    LeaveSession,
    ServerToClientMessage,
)
from row_taker.protocol.transport import ServerTransport
from row_taker.server.local_server import LocalServer
from row_taker.server.outgoing import OutgoingEnvelope
from row_taker.server.server_handle import ServerHandle


@dataclass(slots=True)
class _Connection:
    client_id: str
    transport: ServerTransport
    write_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, envelope: OutgoingEnvelope) -> None:
        with self.write_lock:
            self.transport.send(envelope.message)

    def send_message(self, message: ServerToClientMessage) -> None:
        with self.write_lock:
            self.transport.send(message)

    def close(self) -> None:
        with suppress(Exception):
            self.transport.close()


logger = logging.getLogger("row_taker.server.network")


@dataclass(slots=True)
class NetworkServer:
    server: LocalServer
    _connections: dict[str, _Connection] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _client_counter: int = 0
    _ever_had_connection: bool = False

    def add_connection(
        self, transport: ServerTransport, endpoint_display: str | None = None
    ) -> str:
        with self._lock:
            client_id = f"client-{self._client_counter}"
            self._client_counter += 1
            self._connections[client_id] = _Connection(client_id=client_id, transport=transport)
            self._ever_had_connection = True
            self.server.register_connection(client_id, endpoint_display=endpoint_display)
            logger.info(
                f"connection accepted: client_id={client_id} endpoint={endpoint_display or '-'}"
            )
            return client_id

    def remove_connection(self, client_id: str) -> None:
        with self._lock:
            connection = self._connections.pop(client_id, None)
            if connection is not None:
                connection.close()
            logger.info(f"connection closed: client_id={client_id}")
            self.server.disconnect_client(client_id)
            self._drain_and_dispatch_locked()

    def handle_client_message(self, client_id: str, message: ClientToServerMessage) -> str:
        with self._lock:
            adopted_client_id = self.server.handle_client_message(
                client_id,
                message,
                reply_target_client_id=client_id,
            )
            if adopted_client_id is not None and adopted_client_id != client_id:
                self._rename_connection_locked(client_id, adopted_client_id)
                client_id = adopted_client_id
                logger.info(f"connection adopted requested client id: client_id={client_id}")
            if isinstance(message, JoinLobby):
                connection = self._connections.get(client_id)
                if connection is not None:
                    connection.send_message(IdentityAssigned(client_id=client_id))
            self._drain_and_dispatch_locked()
            return client_id

    def _drain_and_dispatch_locked(self) -> None:
        while True:
            envelopes = self.server.drain_outbox()
            if not envelopes:
                logger.debug("outbox drain: empty")
                return
            logger.debug("outbox drain: envelopes=%s", len(envelopes))
            self._dispatch_locked(envelopes)

    def poll(self) -> None:
        with self._lock:
            self.server.poll()
            self._drain_and_dispatch_locked()

    def should_shutdown(self) -> bool:
        with self._lock:
            return (
                self._ever_had_connection and self.server.should_shutdown and not self._connections
            )

    def _rename_connection_locked(self, old_client_id: str, new_client_id: str) -> None:
        if new_client_id in self._connections:
            raise ValueError(f"connection id already exists: {new_client_id!r}")
        connection = self._connections.pop(old_client_id)
        connection.client_id = new_client_id
        self._connections[new_client_id] = connection

    def _dispatch_locked(self, envelopes: list[OutgoingEnvelope]) -> None:
        failed_client_ids: set[str] = set()
        logger.debug("dispatch envelopes start: count=%s", len(envelopes))
        for envelope in envelopes:
            if envelope.target_client_id is None:
                recipients = list(self._connections.values())
                logger.debug(
                    "dispatch envelope broadcast: type=%s recipients=%s",
                    type(envelope.message).__name__,
                    [c.client_id for c in recipients],
                )
            else:
                connection = self._connections.get(envelope.target_client_id)
                recipients = [] if connection is None else [connection]
                logger.debug(
                    "dispatch envelope targeted: type=%s target=%s connection_found=%s",
                    type(envelope.message).__name__,
                    envelope.target_client_id,
                    connection is not None,
                )
            for connection in recipients:
                if connection.client_id in failed_client_ids:
                    continue
                try:
                    logger.debug(
                        "send envelope start: type=%s target_client_id=%s",
                        type(envelope.message).__name__,
                        connection.client_id,
                    )
                    connection.send(envelope)
                    logger.debug(
                        "send envelope success: type=%s target_client_id=%s",
                        type(envelope.message).__name__,
                        connection.client_id,
                    )
                except TransportError as exc:
                    failed_client_ids.add(connection.client_id)
                    logger.info(
                        f"send failed: client_id={connection.client_id} error={type(exc).__name__}: {exc}"
                    )
        if failed_client_ids:
            for client_id in failed_client_ids:
                connection = self._connections.pop(client_id, None)
                if connection is not None:
                    connection.close()
                self.server.disconnect_client(client_id)
            self._drain_and_dispatch_locked()


SocketAddress = tuple[str, int] | tuple[str, int, int, int] | str | bytes


def _format_endpoint(addr: SocketAddress | None) -> str | None:
    if isinstance(addr, tuple):
        return f"{addr[0]}:{addr[1]}"
    if isinstance(addr, bytes):
        return addr.decode(errors="replace")
    return addr


def _serve_connection(
    conn: socket.socket, network_server: NetworkServer, endpoint_display: str | None
) -> None:
    transport = ServerTransport.from_socket(conn)
    client_id = network_server.add_connection(transport, endpoint_display=endpoint_display)
    try:
        while True:
            try:
                message = transport.receive()
            except ConnectionClosed:
                logger.info(f"client disconnected while receiving: client_id={client_id}")
                break
            except (ProtocolError, TransportError) as exc:
                logger.info(
                    "client transport error: client_id=%s error=%s: %s",
                    client_id,
                    type(exc).__name__,
                    exc,
                )
                break
            client_id = network_server.handle_client_message(client_id, message)
            if isinstance(message, LeaveSession):
                logger.info(f"client requested leave: client_id={client_id}")
                break
    except Exception:
        logger.exception("unexpected server error while handling client_id=%s", client_id)
    finally:
        network_server.remove_connection(client_id)


def run_network_server(
    host: str,
    port: int,
    *,
    rng: random.Random | None = None,
    seat_count: int = 4,
    log_level: str | None = None,
    log_file: str | None = None,
) -> None:
    if rng is None:
        rng = random.Random()
    with socket.create_server((host, port), reuse_port=False) as listener:
        listener.settimeout(0.5)
        actual_host, actual_port = listener.getsockname()[:2]
        logger.info(f"server started on {actual_host}:{actual_port}")
        server_handle = ServerHandle(
            host=actual_host,
            port=actual_port,
            log_level=log_level,
            log_file=log_file,
        )
        local_server = LocalServer(rng=rng, seat_count=seat_count, server_handle=server_handle)
        network_server = NetworkServer(server=local_server)
        try:
            while True:
                network_server.poll()
                if network_server.should_shutdown():
                    logger.info(
                        "session ended and no participants connected anymore; server shutting down"
                    )
                    break
                try:
                    conn, addr = listener.accept()
                except TimeoutError:
                    continue
                thread = threading.Thread(
                    target=_serve_connection,
                    args=(conn, network_server, _format_endpoint(addr)),
                    daemon=True,
                )
                thread.start()
        finally:
            local_server.close()

        logger.info("network server main loop finished")
