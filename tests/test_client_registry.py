from __future__ import annotations

import pytest

from row_taker.participants import ParticipantKind, ParticipantLocation
from row_taker.server.client_registry import ClientRegistry
from row_taker.server.errors import ClientRequestRejected
from row_taker.server.participants import Participant


def _participant(client_id: str, display_name: str) -> Participant:
    return Participant(
        client_id=client_id,
        display_name=display_name,
        kind=ParticipantKind.HUMAN,
        location=ParticipantLocation.REMOTE,
    )


def test_registry_exposes_participants_through_public_queries() -> None:
    registry = ClientRegistry()
    assert registry.is_empty

    alice = _participant("client-0", "Alice")
    bob = _participant("client-1", "Bob")
    registry.register_participant(alice)
    registry.register_participant(bob)

    assert registry.client_ids() == ("client-0", "client-1")
    assert registry.list_participants() == (alice, bob)
    assert not registry.is_empty

    registry.remove_participant("client-0")
    registry.remove_participant("client-1")
    assert registry.is_empty


def test_registry_public_name_validation_supports_excluding_current_client() -> None:
    registry = ClientRegistry()
    registry.register_participant(_participant("client-0", "Alice"))
    registry.register_participant(_participant("client-1", "Bob"))

    assert registry.validate_display_name(" alice ", exclude_client_id="client-0") == "alice"
    with pytest.raises(ClientRequestRejected, match="duplicate participant display name"):
        registry.validate_display_name("ALICE")
