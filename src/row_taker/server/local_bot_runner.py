from __future__ import annotations

from dataclasses import dataclass

from row_taker.clients.client import Client
from row_taker.server.endpoints import LocalLoopbackEndpoint


@dataclass(slots=True)
class LocalBotRunner:
    client: Client
    endpoint: LocalLoopbackEndpoint

    def pump(self) -> int:
        handled_messages = 0
        for message in self.endpoint.drain_incoming():
            handled_messages += 1
            response = self.client.handle_server_message(message)
            if response is not None:
                self.endpoint.send_to_server(response)
        return handled_messages
