from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from row_taker.engine.lobby.state import LobbyState
from row_taker.server.errors import ClientRequestRejected

logger = logging.getLogger("row_taker.server.local_bots")


class BotProcess(Protocol):
    def poll(self) -> int | None: ...

    def close(self) -> None: ...


class LocalBotSpawner(Protocol):
    def spawn_local_bot(
        self,
        *,
        display_name: str,
        client_id: str,
        seed: int,
    ) -> BotProcess: ...


class BotSpawnError(RuntimeError):
    """Raised when one of the local bot child processes cannot be spawned."""


@dataclass(slots=True, frozen=True)
class BotStartupFailure:
    client_id: str
    display_name: str
    message: str


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
    seed: int
    started_at: float
    handle: BotProcess

    def as_spec(self) -> PendingBotSpec:
        return PendingBotSpec(
            seat_index=self.seat_index,
            display_name=self.display_name,
            seed=self.seed,
        )


@dataclass(slots=True)
class LocalBotManager:
    rng: random.Random
    _bot_counter: int = 1
    _pending_by_seat: dict[int, PendingBotSpec] = field(default_factory=dict)
    _pending_starts: dict[str, PendingBotStart] = field(default_factory=dict)
    _startup_starts: dict[str, PendingBotStart] = field(default_factory=dict)
    _running_by_client_id: dict[str, BotProcess] = field(default_factory=dict)

    def reserve(self, seat_index: int, display_name: str) -> PendingBotSpec:
        value = self.validate_display_name(
            display_name,
            exclude_seat_index=seat_index,
        )
        spec = PendingBotSpec(
            seat_index=seat_index,
            display_name=value,
            seed=self.rng.randrange(2**63),
        )
        self._pending_by_seat[seat_index] = spec
        return spec

    def clear_reservation(self, seat_index: int) -> None:
        self._pending_by_seat.pop(seat_index, None)

    def pending_display_names(self) -> dict[int, str]:
        return {seat_index: spec.display_name for seat_index, spec in self._pending_by_seat.items()}

    def validate_display_name(
        self,
        display_name: str,
        *,
        exclude_seat_index: int | None = None,
    ) -> str:
        value = display_name.strip()
        if not value:
            raise ClientRequestRejected("display name must not be empty")
        normalized = value.casefold()
        for seat_index, spec in self._pending_by_seat.items():
            if exclude_seat_index is not None and seat_index == exclude_seat_index:
                continue
            if spec.display_name.strip().casefold() == normalized:
                raise ClientRequestRejected(f"duplicate participant display name: {value!r}")
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
        server_handle: LocalBotSpawner,
        *,
        client_id_in_use: Callable[[str], bool],
        started_at: float,
    ) -> tuple[PendingBotStart, ...]:
        if self._startup_starts:
            raise RuntimeError("local bot startup is already in progress")

        started: list[PendingBotStart] = []
        try:
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
                    seed=spec.seed,
                    started_at=started_at,
                    handle=handle,
                )
                self._pending_starts[client_id] = pending
                self._startup_starts[client_id] = pending
                started.append(pending)
        except Exception as exc:
            logger.exception("failed to spawn local bot process")
            self._rollback_spawned_processes(started)
            raise BotSpawnError("could not spawn all local bot processes") from exc

        return tuple(started)

    def pending_start(self, client_id: str) -> PendingBotStart | None:
        return self._pending_starts.get(client_id)

    def mark_connected(self, client_id: str) -> PendingBotStart:
        pending = self._pending_starts.pop(client_id)
        self._pending_by_seat.pop(pending.seat_index, None)
        self._running_by_client_id[client_id] = pending.handle
        return pending

    def startup_failure(
        self,
        *,
        now: float,
        timeout_seconds: float,
    ) -> BotStartupFailure | None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")

        for start in self._startup_starts.values():
            exit_code = start.handle.poll()
            if exit_code is not None:
                return BotStartupFailure(
                    client_id=start.client_id,
                    display_name=start.display_name,
                    message=(
                        f"local bot {start.display_name!r} exited before joining "
                        f"(exit code {exit_code})"
                    ),
                )
            if now - start.started_at >= timeout_seconds:
                return BotStartupFailure(
                    client_id=start.client_id,
                    display_name=start.display_name,
                    message=(
                        f"local bot {start.display_name!r} did not join within "
                        f"{timeout_seconds:g} seconds"
                    ),
                )
        return None

    def complete_startup(self) -> None:
        if self._pending_starts:
            raise RuntimeError("cannot complete local bot startup while bots are pending")
        self._startup_starts.clear()

    def abort_startup(self) -> tuple[str, ...]:
        client_ids = tuple(self._startup_starts)
        for start in self._startup_starts.values():
            self._pending_by_seat[start.seat_index] = start.as_spec()
            start.handle.close()
        self._pending_starts.clear()
        for client_id in client_ids:
            self._running_by_client_id.pop(client_id, None)
        self._startup_starts.clear()
        return client_ids

    def close_running(self, client_id: str) -> None:
        handle = self._running_by_client_id.pop(client_id, None)
        self._startup_starts.pop(client_id, None)
        self._pending_starts.pop(client_id, None)
        if handle is None:
            return
        logger.debug("closing running bot process: client_id=%s", client_id)
        handle.close()
        logger.debug("closed running bot process: client_id=%s", client_id)

    def close_all(self) -> None:
        self.abort_startup()
        for client_id in tuple(self._running_by_client_id):
            self.close_running(client_id)

    def _rollback_spawned_processes(self, starts: list[PendingBotStart]) -> None:
        for start in starts:
            start.handle.close()
            self._pending_starts.pop(start.client_id, None)
            self._startup_starts.pop(start.client_id, None)

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
