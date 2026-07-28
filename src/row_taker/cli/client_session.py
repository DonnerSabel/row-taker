from __future__ import annotations

import asyncio

from row_taker.cli.app import CliApp
from row_taker.cli.console import CliConsole as _CliConsole
from row_taker.cli.render import render_public_state
from row_taker.cli.terminal import clear_screen
from row_taker.client.state import initial_client_state as _initial_client_state
from row_taker.engine.game.state import PublicState
from row_taker.protocol.transport import ClientTransport

CliConsole = _CliConsole
initial_client_state = _initial_client_state


class ClientSession:
    def __init__(
        self,
        transport: ClientTransport,
        interactive: bool = True,
        own_client_id: str | None = None,
        *,
        console_factory=None,
        initial_state_factory=None,
    ) -> None:
        if console_factory is None:
            console_factory = CliConsole
        if initial_state_factory is None:
            initial_state_factory = initial_client_state
        self.app = CliApp(
            transport=transport,
            own_client_id=own_client_id,
            interactive=interactive,
            console_factory=console_factory,
            initial_state_factory=initial_state_factory,
        )

    @property
    def transport(self) -> ClientTransport:
        return self.app.transport

    @property
    def own_client_id(self) -> str | None:
        return self.app.own_client_id

    def run(self) -> PublicState | None:
        try:
            return asyncio.run(self.run_async())
        except KeyboardInterrupt:
            return None

    async def run_async(self) -> PublicState | None:
        return await self.app.run_async()


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return
    clear_screen()
    render_public_state(public_state)
    print("Endstand:")
    ranking = sorted(public_state.players, key=lambda player: (player.score, player.name))
    for place, player in enumerate(ranking, start=1):
        print(f"  {place}. {player.name}: {player.score} Punkte")
