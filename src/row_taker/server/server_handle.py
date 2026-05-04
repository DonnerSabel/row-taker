from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from row_taker.server.bot_process_handle import BotProcessHandle


@dataclass(slots=True, frozen=True)
class ServerHandle:
    host: str
    port: int
    python_executable: str = sys.executable
    log_level: str | None = None
    log_file: str | None = None

    def spawn_local_bot(self, *, display_name: str, client_id: str, seed: int) -> BotProcessHandle:
        connect_host = self._connect_host()
        return BotProcessHandle.spawn(
            host=connect_host,
            port=self.port,
            display_name=display_name,
            client_id=client_id,
            seed=seed,
            python_executable=self.python_executable,
            log_level=self.log_level,
            log_file=self._bot_log_file(client_id),
        )

    def _connect_host(self) -> str:
        if self.host in {"0.0.0.0", "::"}:
            return "127.0.0.1"
        return self.host

    def _bot_log_file(self, client_id: str) -> str | None:
        if not self.log_file:
            return None
        path = Path(self.log_file)
        stem = path.stem or path.name
        suffix = path.suffix or ".log"
        return str(path.with_name(f"{stem}-{client_id}{suffix}"))
