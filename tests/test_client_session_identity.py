from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from row_taker.cli.client_session import ClientSession
from row_taker.protocol.messages import (
    AssignSeatToClient,
    IdentityAssigned,
    LobbyParticipantView,
    LobbySeatView,
    LobbyView,
)


@dataclass
class _FakeTransport:
    sent_messages: list[object] = field(default_factory=list)
    sock: object = field(default_factory=object)

    def send(self, message: object) -> None:
        self.sent_messages.append(message)

    def close(self) -> None:
        pass


@dataclass
class _FakeUiClient:
    def handle_server_message(self, message: object) -> object | None:
        return None


def _lobby() -> LobbyView:
    return LobbyView(
        seat_count=3,
        participants=(
            LobbyParticipantView(
                client_id="client-1",
                display_name="Alice",
                participant_kind="human",
                seat_index=None,
            ),
            LobbyParticipantView(
                client_id="client-2", display_name="Bob", participant_kind="human", seat_index=1
            ),
            LobbyParticipantView(
                client_id="pending-bot-seat-2",
                display_name="Bot_1",
                participant_kind="bot",
                seat_index=2,
            ),
        ),
        seats=(
            LobbySeatView(
                seat_index=0,
                occupant_client_id=None,
                occupant_display_name=None,
                occupant_kind=None,
            ),
            LobbySeatView(
                seat_index=1,
                occupant_client_id="client-2",
                occupant_display_name="Bob",
                occupant_kind="human",
            ),
            LobbySeatView(
                seat_index=2,
                occupant_client_id="pending-bot-seat-2",
                occupant_display_name="Bot_1",
                occupant_kind="bot",
            ),
        ),
        game_started=False,
    )


def test_client_session_stores_own_client_id_from_identity_assigned() -> None:
    session = ClientSession(
        transport=_FakeTransport(), ui_client=_FakeUiClient(), interactive=False
    )

    latest_lobby, latest_public_state, lobby_mode, finished = session._handle_message(
        IdentityAssigned(client_id="client-1"),
        None,
        None,
        ("main", None),
    )

    assert session.own_client_id == "client-1"
    assert latest_lobby is None
    assert latest_public_state is None
    assert lobby_mode == ("main", None)
    assert finished is False


def test_assign_seat_uses_explicit_own_client_id() -> None:
    transport = _FakeTransport()
    session = ClientSession(
        transport=transport, ui_client=_FakeUiClient(), interactive=False, own_client_id="client-1"
    )

    mode = session._handle_lobby_command(_lobby(), ("seat", 0), "m")

    assert mode == ("main", None)
    assert transport.sent_messages == [
        AssignSeatToClient(seat_index=0, target_client_id="client-1")
    ]


def test_assign_seat_without_identity_does_not_crash(capsys: pytest.CaptureFixture[str]) -> None:
    transport = _FakeTransport()
    session = ClientSession(transport=transport, ui_client=_FakeUiClient(), interactive=False)

    mode = session._handle_lobby_command(_lobby(), ("seat", 0), "m")

    assert mode == ("main", None)
    assert transport.sent_messages == []
    assert "client_id" in capsys.readouterr().out


def test_render_lobby_shows_participants_and_marks_own_client(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("row_taker.cli.client_session.clear_screen", lambda: None)
    session = ClientSession(
        transport=_FakeTransport(),
        ui_client=_FakeUiClient(),
        interactive=False,
        own_client_id="client-1",
    )

    session._render_lobby(_lobby(), ("main", None))

    out = capsys.readouterr().out
    assert "Teilnehmer" in out
    assert "Alice (human, nicht gesetzt) <- du" in out
    assert "Bob (human, Platz 1)" in out
    assert "Bot_1 (bot, Platz 2)" in out
