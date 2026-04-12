from __future__ import annotations

import random
import socket
import threading
from dataclasses import dataclass, field

from row_taker.protocol.errors import ConnectionClosed, ProtocolError, TransportError
from row_taker.protocol.messages import ClientToServerMessage, IdentityAssigned, JoinLobby
from row_taker.protocol.transport import ServerTransport
from row_taker.server.local_server import LocalServer, OutgoingEnvelope
from row_taker.server.server_handle import ServerHandle


@dataclass(slots=True)
class _Connection:
    client_id: str
    transport: ServerTransport
    write_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, envelope: OutgoingEnvelope) -> None:
        with self.write_lock:
            self.transport.send(envelope.message)

    def send_message(self, message: object) -> None:
        with self.write_lock:
            self.transport.send(message)


@dataclass(slots=True)
class NetworkServer:
    server: LocalServer
    _connections: dict[str, _Connection] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _client_counter: int = 0
    _ever_had_connection: bool = False

    def add_connection(self, transport: ServerTransport, endpoint_display: str | None = None) -> str:
        with self._lock:
            client_id = f"client-{self._client_counter}"
            self._client_counter += 1
            self._connections[client_id] = _Connection(client_id=client_id, transport=transport)
            self._ever_had_connection = True
            self.server.register_connection(client_id, endpoint_display=endpoint_display)
            return client_id

    def remove_connection(self, client_id: str) -> None:
        with self._lock:
            self._connections.pop(client_id, None)
            self.server.disconnect_client(client_id)
            self._dispatch_locked(self.server.drain_outbox())

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
            if isinstance(message, JoinLobby):
                connection = self._connections.get(client_id)
                if connection is not None:
                    connection.send_message(IdentityAssigned(client_id=client_id))
            self._dispatch_locked(self.server.drain_outbox())
            return client_id

    def should_shutdown(self) -> bool:
        with self._lock:
            return self._ever_had_connection and self.server.should_shutdown and not self._connections

    def _rename_connection_locked(self, old_client_id: str, new_client_id: str) -> None:
        if new_client_id in self._connections:
            raise ValueError(f"connection id already exists: {new_client_id!r}")
        connection = self._connections.pop(old_client_id)
        connection.client_id = new_client_id
        self._connections[new_client_id] = connection

    def _dispatch_locked(self, envelopes: list[OutgoingEnvelope]) -> None:
        for envelope in envelopes:
            if envelope.target_client_id is None:
                for connection in list(self._connections.values()):
                    connection.send(envelope)
            else:
                connection = self._connections.get(envelope.target_client_id)
                if connection is not None:
                    connection.send(envelope)


def _format_endpoint(addr: object) -> str | None:
    if isinstance(addr, tuple) and len(addr) >= 2:
        return f"{addr[0]}:{addr[1]}"
    return None if addr is None else str(addr)


def _serve_connection(conn: socket.socket, network_server: NetworkServer, endpoint_display: str | None) -> None:
    transport = ServerTransport.from_socket(conn)
    client_id = network_server.add_connection(transport, endpoint_display=endpoint_display)
    try:
        while True:
            try:
                message = transport.receive()
            except ConnectionClosed:
                break
            except (ProtocolError, TransportError):
                break
            client_id = network_server.handle_client_message(client_id, message)
    finally:
        try:
            network_server.remove_connection(client_id)
        finally:
            transport.close()


def run_network_server(
    host: str, port: int, *, rng: random.Random | None = None, seat_count: int = 4
) -> None:
    if rng is None:
        rng = random.Random()
    with socket.create_server((host, port), reuse_port=False) as listener:
        listener.settimeout(0.5)
        actual_host, actual_port = listener.getsockname()[:2]
        print(f"Server gestartet auf {actual_host}:{actual_port}", flush=True)
        server_handle = ServerHandle(host=actual_host, port=actual_port)
        local_server = LocalServer(rng=rng, seat_count=seat_count, server_handle=server_handle)
        network_server = NetworkServer(server=local_server)
        while True:
            if network_server.should_shutdown():
                print("Keine Teilnehmer mehr verbunden. Server beendet sich.", flush=True)
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
