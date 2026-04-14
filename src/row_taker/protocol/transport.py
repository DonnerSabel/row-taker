from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from typing import BinaryIO

from row_taker.protocol.errors import ConnectionClosed, ConnectionFailed, ReceiveFailed, SendFailed
from row_taker.protocol.framing import (
    decode_client_message,
    decode_server_message,
    encode_client_message,
    encode_server_message,
)
from row_taker.protocol.messages import ClientToServerMessage, ServerToClientMessage

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TcpLineTransport:
    sock: socket.socket
    reader: BinaryIO
    writer: BinaryIO

    @classmethod
    def connect(cls, host: str, port: int) -> TcpLineTransport:
        try:
            sock = socket.create_connection((host, port))
        except OSError as exc:
            raise ConnectionFailed(str(exc)) from exc
        return cls.from_socket(sock)

    @classmethod
    def from_socket(cls, sock: socket.socket) -> TcpLineTransport:
        return cls(sock=sock, reader=sock.makefile("rb"), writer=sock.makefile("wb"))

    def send_line(self, data: bytes) -> None:
        try:
            self.writer.write(data)
            self.writer.flush()
        except OSError as exc:
            raise SendFailed(str(exc)) from exc

    def receive_line(self) -> bytes:
        try:
            line = self.reader.readline()
        except OSError as exc:
            raise ReceiveFailed(str(exc)) from exc
        if not line:
            raise ConnectionClosed("connection closed")
        return line

    def close(self) -> None:
        logger.debug("transport close start")

        sock = self.sock
        reader = self.reader
        writer = self.writer

        # Break references first so concurrent cleanup paths cannot race the
        # same objects.
        self.sock = None  # type: ignore[assignment]
        self.reader = None  # type: ignore[assignment]
        self.writer = None  # type: ignore[assignment]

        if sock is not None:
            try:
                logger.debug("transport socket shutdown start")
                sock.shutdown(socket.SHUT_RDWR)
                logger.debug("transport socket shutdown done")
            except OSError as exc:
                logger.debug("transport socket shutdown ignored: %s", exc)

            try:
                logger.debug("transport socket close start")
                sock.close()
                logger.debug("transport socket close done")
            except OSError as exc:
                logger.debug("transport socket close ignored: %s", exc)

        if reader is not None:
            try:
                logger.debug("transport reader close start")
                reader.close()
                logger.debug("transport reader close done")
            except OSError as exc:
                logger.debug("transport reader close ignored: %s", exc)

        if writer is not None:
            try:
                logger.debug("transport writer close start")
                writer.close()
                logger.debug("transport writer close done")
            except OSError as exc:
                logger.debug("transport writer close ignored: %s", exc)


@dataclass(slots=True)
class ClientTransport:
    line_transport: TcpLineTransport

    @classmethod
    def connect(cls, host: str, port: int) -> ClientTransport:
        return cls(TcpLineTransport.connect(host, port))

    @property
    def sock(self) -> socket.socket:
        return self.line_transport.sock

    def send(self, message: ClientToServerMessage) -> None:
        self.line_transport.send_line(encode_client_message(message))

    def receive(self) -> ServerToClientMessage:
        return decode_server_message(self.line_transport.receive_line())

    def close(self) -> None:
        self.line_transport.close()


@dataclass(slots=True)
class ServerTransport:
    line_transport: TcpLineTransport

    @classmethod
    def from_socket(cls, sock: socket.socket) -> ServerTransport:
        return cls(TcpLineTransport.from_socket(sock))

    @property
    def sock(self) -> socket.socket:
        return self.line_transport.sock

    def send(self, message: ServerToClientMessage) -> None:
        self.line_transport.send_line(encode_server_message(message))

    def receive(self) -> ClientToServerMessage:
        return decode_client_message(self.line_transport.receive_line())

    def close(self) -> None:
        self.line_transport.close()
