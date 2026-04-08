from __future__ import annotations

import random
from dataclasses import dataclass, field

from row_taker.protocol.messages import IdentityAssigned, JoinLobby, LobbyStateUpdated
from row_taker.server.local_server import LocalServer
from row_taker.server.network_server import NetworkServer


@dataclass
class _FakeTransport:
    sent_messages: list[object] = field(default_factory=list)

    def send(self, message: object) -> None:
        self.sent_messages.append(message)

    def close(self) -> None:
        pass


def test_join_sends_identity_assigned_to_joining_client() -> None:
    network_server = NetworkServer(server=LocalServer(rng=random.Random(1234), seat_count=3))
    transport = _FakeTransport()

    client_id = network_server.add_connection(transport)
    final_client_id = network_server.handle_client_message(client_id, JoinLobby(display_name="Alice"))

    assert final_client_id == client_id
    assert isinstance(transport.sent_messages[0], IdentityAssigned)
    assert transport.sent_messages[0].client_id == client_id
    assert isinstance(transport.sent_messages[1], LobbyStateUpdated)


def test_two_humans_each_receive_their_own_identity_assigned() -> None:
    network_server = NetworkServer(server=LocalServer(rng=random.Random(1234), seat_count=3))
    transport_a = _FakeTransport()
    transport_b = _FakeTransport()

    client_id_a = network_server.add_connection(transport_a)
    client_id_b = network_server.add_connection(transport_b)

    final_a = network_server.handle_client_message(client_id_a, JoinLobby(display_name="Alice"))
    final_b = network_server.handle_client_message(client_id_b, JoinLobby(display_name="Bob"))

    assert final_a == client_id_a
    assert final_b == client_id_b
    assert IdentityAssigned(client_id=client_id_a) in transport_a.sent_messages
    assert IdentityAssigned(client_id=client_id_b) in transport_b.sent_messages
