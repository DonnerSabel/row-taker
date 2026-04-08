from __future__ import annotations


class TransportError(Exception):
    pass


class ConnectionClosed(TransportError):
    pass


class ConnectionFailed(TransportError):
    pass


class ReceiveFailed(TransportError):
    pass


class SendFailed(TransportError):
    pass


class ProtocolError(TransportError):
    pass


class MessageDecodeError(ProtocolError):
    pass


class MessageEncodeError(ProtocolError):
    pass
