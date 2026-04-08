from __future__ import annotations

import random
import socket
import threading
from dataclasses import dataclass, field

from row_taker.protocol.errors import ConnectionClosed, ProtocolError, TransportError
from row_taker.protocol.messages import ClientToServerMessage
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


@dataclass(slots=True)
class NetworkServer:
    server: LocalServer
    _connections: dict[str, _Connection] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _client_counter: int = 0

    def add_connection(self, transport: ServerTransport) -> str:
        with self._lock:
            client_id = f"client-{self._client_counter}"
            self._client_counter += 1
            self._connections[client_id] = _Connection(client_id=client_id, transport=transport)
            self.server.register_connection(client_id)
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
            self._dispatch_locked(self.server.drain_outbox())
            return client_id

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


def _serve_connection(conn: socket.socket, network_server: NetworkServer) -> None:
    transport = ServerTransport.from_socket(conn)
    client_id = network_server.add_connection(transport)
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


def run_network_server(host: str, port: int, *, rng: random.Random | None = None, seat_count: int = 4) -> None:
    if rng is None:
        rng = random.Random()
    with socket.create_server((host, port), reuse_port=False) as listener:
        server_handle = ServerHandle(host=host, port=listener.getsockname()[1])
        local_server = LocalServer(rng=rng, seat_count=seat_count, server_handle=server_handle)
        network_server = NetworkServer(server=local_server)
        while True:
            conn, _addr = listener.accept()
            thread = threading.Thread(target=_serve_connection, args=(conn, network_server), daemon=True)
            thread.start()


@dataclass(slots=True)
class BackgroundServerHandle:
    host: str
    port: int
    _thread: threading.Thread

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout)


def start_background_network_server(host: str = "127.0.0.1", port: int = 0, *, seat_count: int = 4) -> BackgroundServerHandle:
    ready = threading.Event()
    selected_port: list[int] = []

    def worker() -> None:
        with socket.create_server((host, port), reuse_port=False) as listener:
            selected_port.append(listener.getsockname()[1])
            server_handle = ServerHandle(host=host, port=selected_port[0])
            ready.set()
            network_server = NetworkServer(
                server=LocalServer(
                    rng=random.Random(),
                    seat_count=seat_count,
                    server_handle=server_handle,
                )
            )
            while True:
                conn, _addr = listener.accept()
                thread = threading.Thread(target=_serve_connection, args=(conn, network_server), daemon=True)
                thread.start()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    ready.wait(timeout=5)
    if not selected_port:
        raise RuntimeError("background network server failed to start")
    return BackgroundServerHandle(host=host, port=selected_port[0], _thread=thread)
