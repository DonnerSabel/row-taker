from __future__ import annotations

from dataclasses import dataclass
import sys

from row_taker.server.bot_process_handle import BotProcessHandle


@dataclass(slots=True, frozen=True)
class ServerHandle:
    host: str
    port: int
    python_executable: str = sys.executable

    def spawn_local_bot(self, *, display_name: str, client_id: str, seed: int) -> BotProcessHandle:
        connect_host = self._connect_host()
        return BotProcessHandle.spawn(
            host=connect_host,
            port=self.port,
            display_name=display_name,
            client_id=client_id,
            seed=seed,
            python_executable=self.python_executable,
        )

    def _connect_host(self) -> str:
        if self.host in {"0.0.0.0", "::"}:
            return "127.0.0.1"
        return self.host
