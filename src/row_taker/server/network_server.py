from __future__ import annotations

import random
import socket
import threading
from dataclasses import dataclass, field
from typing import TextIO

from row_taker.protocol.framing import decode_client_message, encode_server_message
from row_taker.server.local_server import LocalServer, OutgoingEnvelope


@dataclass(slots=True)
class _Connection:
    client_id: str
    writer: TextIO
    write_lock: threading.Lock = field(default_factory=threading.Lock)

    def send(self, envelope: OutgoingEnvelope) -> None:
        payload = encode_server_message(envelope.message).decode('utf-8')
        with self.write_lock:
            self.writer.write(payload)
            self.writer.flush()


@dataclass(slots=True)
class NetworkServer:
    server: LocalServer
    _connections: dict[str, _Connection] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)
    _client_counter: int = 0

    def add_connection(self, writer: TextIO) -> str:
        with self._lock:
            client_id = f'client-{self._client_counter}'
            self._client_counter += 1
            self._connections[client_id] = _Connection(client_id=client_id, writer=writer)
            self.server.register_connection(client_id)
            return client_id

    def remove_connection(self, client_id: str) -> None:
        with self._lock:
            self._connections.pop(client_id, None)
            self.server.disconnect_client(client_id)
            self._dispatch_locked(self.server.drain_outbox())

    def handle_client_message_bytes(self, client_id: str, data: bytes) -> None:
        with self._lock:
            message = decode_client_message(data)
            self.server.handle_client_message(client_id, message)
            self._dispatch_locked(self.server.drain_outbox())

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
    with conn:
        reader: TextIO = conn.makefile('r', encoding='utf-8', newline='\n')
        writer: TextIO = conn.makefile('w', encoding='utf-8', newline='\n')
        client_id = network_server.add_connection(writer)
        try:
            for line in reader:
                network_server.handle_client_message_bytes(client_id, line.encode('utf-8'))
        finally:
            try:
                network_server.remove_connection(client_id)
            finally:
                writer.close()
                reader.close()


def run_network_server(host: str, port: int, *, rng: random.Random | None = None, seat_count: int = 4) -> None:
    if rng is None:
        rng = random.Random()
    local_server = LocalServer(rng=rng, seat_count=seat_count)
    network_server = NetworkServer(server=local_server)
    with socket.create_server((host, port), reuse_port=False) as listener:
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


def start_background_network_server(host: str = '127.0.0.1', port: int = 0, *, seat_count: int = 4) -> BackgroundServerHandle:
    ready = threading.Event()
    selected_port: list[int] = []

    def worker() -> None:
        with socket.create_server((host, port), reuse_port=False) as listener:
            selected_port.append(listener.getsockname()[1])
            ready.set()
            network_server = NetworkServer(server=LocalServer(rng=random.Random(), seat_count=seat_count))
            while True:
                conn, _addr = listener.accept()
                thread = threading.Thread(target=_serve_connection, args=(conn, network_server), daemon=True)
                thread.start()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    ready.wait(timeout=5)
    if not selected_port:
        raise RuntimeError('background network server failed to start')
    return BackgroundServerHandle(host=host, port=selected_port[0], _thread=thread)
