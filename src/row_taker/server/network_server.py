from __future__ import annotations

import random
import socket
import threading
from dataclasses import dataclass, field
from typing import TextIO

from row_taker.clients.random_bot_client import RandomBotClient
from row_taker.engine.lobby.config import ClientKind, MatchConfig
from row_taker.protocol.framing import decode_client_message, encode_server_message
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ConfigureLobby,
    ServerError,
)
from row_taker.server.local_server import LocalServer


@dataclass(slots=True)
class NetworkServer:
    server: LocalServer
    bot_clients_by_player_id: dict[str, RandomBotClient] = field(default_factory=dict)

    def handle_client_message_bytes(self, data: bytes) -> list[bytes]:
        try:
            message = decode_client_message(data)
            if isinstance(message, ConfigureLobby):
                self._configure_bot_clients(message.match_config)
            self.server.handle_client_message(message)
            messages = self._drain_visible_messages()
            return [encode_server_message(message) for message in messages]
        except Exception as exc:
            error = ServerError(message=str(exc))
            return [encode_server_message(error)]

    def _configure_bot_clients(self, match_config: MatchConfig) -> None:
        human_count = sum(1 for seat in match_config.seats if seat.kind == ClientKind.HUMAN)
        if human_count != 1:
            raise ValueError("network mode currently requires exactly one human seat")

        self.bot_clients_by_player_id = {}
        for seat in match_config.seats:
            if seat.kind == ClientKind.RANDOM_BOT:
                player_id = f"player-{seat.seat_index}"
                self.bot_clients_by_player_id[player_id] = RandomBotClient(rng=self.server.rng)

    def _drain_visible_messages(self):
        visible = []
        pending = self.server.drain_outbox()
        while pending:
            follow_up = []
            for message in pending:
                if isinstance(message, (ChooseCardRequested, ChooseRowRequested)) and message.player_id in self.bot_clients_by_player_id:
                    response = self.bot_clients_by_player_id[message.player_id].handle_server_message(message)
                    if response is not None:
                        self.server.handle_client_message(response)
                        follow_up.extend(self.server.drain_outbox())
                    continue
                visible.append(message)
            pending = follow_up
        return visible


def _serve_connection(conn: socket.socket, network_server: NetworkServer) -> None:
    with conn:
        reader: TextIO = conn.makefile("r", encoding="utf-8", newline="\n")
        writer: TextIO = conn.makefile("w", encoding="utf-8", newline="\n")
        try:
            for line in reader:
                payload = line.encode("utf-8")
                for response_bytes in network_server.handle_client_message_bytes(payload):
                    writer.write(response_bytes.decode("utf-8"))
                writer.flush()
        finally:
            writer.close()
            reader.close()


def run_network_server(host: str, port: int, *, rng: random.Random | None = None) -> None:
    if rng is None:
        rng = random.Random()
    local_server = LocalServer(rng=rng)
    network_server = NetworkServer(server=local_server)
    with socket.create_server((host, port), reuse_port=False) as listener:
        conn, _addr = listener.accept()
        _serve_connection(conn, network_server)


@dataclass(slots=True)
class BackgroundServerHandle:
    host: str
    port: int
    _thread: threading.Thread

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout)


def start_background_network_server(host: str = "127.0.0.1", port: int = 0) -> BackgroundServerHandle:
    ready = threading.Event()
    selected_port: list[int] = []

    def worker() -> None:
        with socket.create_server((host, port), reuse_port=False) as listener:
            selected_port.append(listener.getsockname()[1])
            ready.set()
            conn, _addr = listener.accept()
            network_server = NetworkServer(server=LocalServer(rng=random.Random()))
            _serve_connection(conn, network_server)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    ready.wait(timeout=5)
    if not selected_port:
        raise RuntimeError("background network server failed to start")
    return BackgroundServerHandle(host=host, port=selected_port[0], _thread=thread)
