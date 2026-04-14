from __future__ import annotations

from row_taker.cli.app import CliApp
from row_taker.cli.console import CliConsole
from row_taker.cli.state_models import initial_cli_state
from row_taker.engine.game.state import PublicState
from row_taker.protocol.transport import ClientTransport


class ClientSession:
    def __init__(
        self,
        transport: ClientTransport,
        own_client_id: str | None = None,
        *,
        interactive: bool = True,
        console_factory: type[CliConsole] = CliConsole,
        initial_state_factory=initial_cli_state,
    ) -> None:
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

    async def run_async(self) -> PublicState | None:
        return await self.app.run_async()


def print_final_result(public_state: PublicState | None) -> None:
    if public_state is None:
        return
    print("Endstand:")
    ranking = sorted(public_state.players, key=lambda player: (player.score, player.name))
    for place, player in enumerate(ranking, start=1):
        print(f"  {place}. {player.name}: {player.score} Punkte")
