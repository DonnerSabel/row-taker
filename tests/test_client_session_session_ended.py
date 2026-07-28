from __future__ import annotations

import asyncio

from row_taker.cli.client_session import ClientSession
from row_taker.protocol.messages import SessionEnded, SessionEndReason


class _FakeConsole:
    instances: list[_FakeConsole] = []

    def __init__(self) -> None:
        self.renders: list[tuple[str, str | None]] = []
        self.closed = False
        type(self).instances.append(self)

    async def render(self, screen: str, prompt: str | None) -> None:
        self.renders.append((screen, prompt))

    async def read_line(self) -> str:
        await asyncio.Future()
        raise AssertionError("unreachable")

    async def close(self) -> None:
        self.closed = True


class _FakeTransport:
    def __init__(self) -> None:
        self.closed = False

    def receive(self) -> SessionEnded:
        return SessionEnded(
            message="Spiel abgebrochen: Hugo hat die Sitzung verlassen.",
            reason=SessionEndReason.QUIT,
            client_id="client-1",
            display_name="Hugo",
        )

    def send(self, _message: object) -> None:
        raise AssertionError("send() should not be called in this test")

    def close(self) -> None:
        self.closed = True


def test_session_ended_clears_prompt_before_shutdown() -> None:
    transport = _FakeTransport()
    session = ClientSession(transport=transport, console_factory=_FakeConsole)

    result = asyncio.run(session.run_async())

    assert result is None
    assert transport.closed is True
    console = _FakeConsole.instances[-1]
    assert console.closed is True
    assert console.renders[-1][1] is None
    assert "Spiel abgebrochen" in console.renders[-1][0]


class _QueuedTransport:
    def __init__(self, messages: list[object]) -> None:
        self._messages = list(messages)
        self.closed = False

    def receive(self) -> object:
        from row_taker.protocol.errors import ConnectionClosed

        if self._messages:
            return self._messages.pop(0)
        raise ConnectionClosed("done")

    def send(self, _message: object) -> None:
        raise AssertionError("send() should not be called in this test")

    def close(self) -> None:
        self.closed = True


def test_client_session_applies_game_messages_one_by_one_around_presentation_queue() -> None:
    import random

    from row_taker.client.core_state import ClientCoreState, PendingAction
    from row_taker.client.state import ClientState, enter_game_mode
    from row_taker.engine.game import build_player_state, setup_game
    from row_taker.protocol.messages import CardsRevealed, PlayedCardView, StateUpdated

    game = setup_game(["Alice", "Bob"], rng=random.Random(123))
    player_state = build_player_state(game, game.players[0].player_id)
    public_state = player_state.public_state

    def _initial_state(_own_client_id=None) -> ClientState:
        state = ClientState(core_state=ClientCoreState(public_state=public_state))
        return enter_game_mode(state, pending_action=PendingAction.NONE)

    messages = [
        StateUpdated(state=public_state),
        CardsRevealed(
            plays=(
                PlayedCardView(
                    player_id=public_state.players[0].player_id,
                    player_name=public_state.players[0].name,
                    card_value=104,
                ),
            )
        ),
        StateUpdated(state=public_state),
        SessionEnded(
            message="Spiel abgebrochen: Test.",
            reason=SessionEndReason.QUIT,
            client_id="client-1",
            display_name="Test",
        ),
    ]
    transport = _QueuedTransport(messages)
    session = ClientSession(
        transport=transport,
        interactive=False,
        console_factory=_FakeConsole,
        initial_state_factory=_initial_state,
    )

    result = asyncio.run(session.run_async())

    assert result is None
    console = _FakeConsole.instances[-1]
    rendered_bodies = [body for body, _prompt in console.renders]
    assert any("Lokale Auflösung:" in body for body in rendered_bodies)
    first_resolution_index = next(
        i for i, body in enumerate(rendered_bodies) if "Lokale Auflösung:" in body
    )
    assert first_resolution_index > 0
