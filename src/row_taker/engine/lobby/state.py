from __future__ import annotations

from dataclasses import dataclass

from row_taker.engine.lobby.config import MatchConfig


@dataclass(slots=True, frozen=True)
class LobbyState:
    match_config: MatchConfig | None = None
    game_started: bool = False

    @property
    def is_configured(self) -> bool:
        return self.match_config is not None
