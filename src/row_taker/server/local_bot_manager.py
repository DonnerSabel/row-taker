from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field

from row_taker.engine.lobby.state import LobbyState
from row_taker.server.bot_process_handle import BotProcessHandle
from row_taker.server.server_handle import ServerHandle

logger = logging.getLogger("row_taker.server.local_bots")


@dataclass(slots=True, frozen=True)
class PendingBotSpec:
    seat_index: int
    display_name: str
    seed: int


@dataclass(slots=True)
class PendingBotStart:
    client_id: str
    seat_index: int
    display_name: str
    handle: BotProcessHandle


@dataclass(slots=True)
class LocalBotManager:
    rng: random.Random
    _bot_counter: int = 1
    _pending_by_seat: dict[int, PendingBotSpec] = field(default_factory=dict)
    _pending_starts: dict[str, PendingBotStart] = field(default_factory=dict)
    _running_by_client_id: dict[str, BotProcessHandle] = field(default_factory=dict)

    def reserve(self, seat_index: int, display_name: str) -> PendingBotSpec:
        spec = PendingBotSpec(
            seat_index=seat_index,
            display_name=display_name,
            seed=self.rng.randrange(2**63),
        )
        self._pending_by_seat[seat_index] = spec
        return spec

    def clear_reservation(self, seat_index: int) -> None:
        self._pending_by_seat.pop(seat_index, None)

    def pending_display_names(self) -> dict[int, str]:
        return {seat_index: spec.display_name for seat_index, spec in self._pending_by_seat.items()}

    def normalize_pending_display_name(self, display_name: str) -> str:
        value = display_name.strip()
        normalized = value.casefold()
        for spec in self._pending_by_seat.values():
            if spec.display_name.casefold() == normalized:
                return spec.display_name
        return value

    def can_complete_lobby(self, lobby_state: LobbyState) -> bool:
        if lobby_state.game_started:
            return False
        occupied_humans = {
            seat.seat_index for seat in lobby_state.seats if seat.occupant_client_id is not None
        }
        occupied = occupied_humans | set(self._pending_by_seat)
        return len(occupied) >= 2 and len(occupied) == lobby_state.seat_count

    @property
    def has_pending_reservations(self) -> bool:
        return bool(self._pending_by_seat)

    @property
    def has_pending_starts(self) -> bool:
        return bool(self._pending_starts)

    @property
    def has_running_bots(self) -> bool:
        return bool(self._running_by_client_id)

    def spawn_pending(
        self,
        server_handle: ServerHandle,
        *,
        client_id_in_use: Callable[[str], bool],
    ) -> tuple[PendingBotStart, ...]:
        started: list[PendingBotStart] = []
        for seat_index, spec in sorted(self._pending_by_seat.items()):
            client_id = self._next_client_id(client_id_in_use)
            handle = server_handle.spawn_local_bot(
                display_name=spec.display_name,
                client_id=client_id,
                seed=spec.seed,
            )
            pending = PendingBotStart(
                client_id=client_id,
                seat_index=seat_index,
                display_name=spec.display_name,
                handle=handle,
            )
            self._pending_starts[client_id] = pending
            started.append(pending)
        return tuple(started)

    def pending_start(self, client_id: str) -> PendingBotStart | None:
        return self._pending_starts.get(client_id)

    def mark_connected(self, client_id: str) -> PendingBotStart:
        pending = self._pending_starts.pop(client_id)
        self._pending_by_seat.pop(pending.seat_index, None)
        self._running_by_client_id[client_id] = pending.handle
        return pending

    def abort_startup(self) -> None:
        for pending in self._pending_starts.values():
            pending.handle.close()
        self._pending_starts.clear()

    def close_running(self, client_id: str) -> None:
        handle = self._running_by_client_id.pop(client_id, None)
        if handle is None:
            return
        logger.debug("closing running bot process: client_id=%s", client_id)
        handle.close()
        logger.debug("closed running bot process: client_id=%s", client_id)

    def close_all(self) -> None:
        self.abort_startup()
        for client_id in tuple(self._running_by_client_id):
            self.close_running(client_id)

    def _next_client_id(self, client_id_in_use: Callable[[str], bool]) -> str:
        while True:
            client_id = f"bot-{self._bot_counter}"
            self._bot_counter += 1
            if (
                not client_id_in_use(client_id)
                and client_id not in self._pending_starts
                and client_id not in self._running_by_client_id
            ):
                return client_id
