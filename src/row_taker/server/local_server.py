from __future__ import annotations

from dataclasses import dataclass, field
import random

from row_taker.engine.game import setup_game
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.state import GameState, PublicState
from row_taker.engine.lobby.rules import assign_client_to_seat, clear_seat, mark_game_started, remove_client
from row_taker.engine.lobby.state import LobbyState
from row_taker.hub.match_hub import MatchHub
from row_taker.protocol.messages import (
    AssignSeatToClient,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameStarting,
    GameServerMessage,
    JoinLobby,
    LobbyActionRejected,
    RequestStartGame,
    ServerToClientMessage,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)
from row_taker.server.bot_process_handle import BotProcessHandle
from row_taker.server.client_registry import ClientRegistry
from row_taker.server.lobby_view import build_lobby_state_updated, build_lobby_view
from row_taker.server.match_participants import build_match_participants
from row_taker.server.participants import Participant, ParticipantKind, ParticipantLocation
from row_taker.server.server_handle import ServerHandle


@dataclass(slots=True, frozen=True)
class OutgoingEnvelope:
    message: ServerToClientMessage
    target_client_id: str | None = None


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
class LocalServer:
    rng: random.Random
    seat_count: int = 4
    server_handle: ServerHandle | None = None
    lobby_state: LobbyState = field(default_factory=LobbyState)
    active_match: MatchHub | None = None
    outbox: list[OutgoingEnvelope] = field(default_factory=list)
    registry: ClientRegistry = field(default_factory=ClientRegistry)
    player_to_client_id: dict[PlayerID, str] = field(default_factory=dict)
    client_to_player_id: dict[str, PlayerID] = field(default_factory=dict)
    _bot_counter: int = 1
    _pending_bot_seats: dict[int, PendingBotSpec] = field(default_factory=dict)
    _pending_bot_starts: dict[str, PendingBotStart] = field(default_factory=dict)
    _running_bot_processes_by_client_id: dict[str, BotProcessHandle] = field(default_factory=dict)
    _start_in_progress: bool = False

    def __post_init__(self) -> None:
        self.lobby_state = LobbyState(seat_count=self.seat_count)

    def register_connection(self, client_id: str) -> None:
        pass

    def disconnect_client(self, client_id: str) -> None:
        if self.registry.has(client_id):
            kind = self.registry.get_participant(client_id).kind
            if self.active_match is None:
                self._remove_participant(client_id)
                if self._start_in_progress and kind == ParticipantKind.BOT:
                    self._abort_startup()
                self._broadcast_lobby_state()
            elif kind == ParticipantKind.HUMAN:
                self.client_to_player_id.pop(client_id, None)
                self.registry.remove_participant(client_id)
            else:
                self._close_running_bot(client_id)
                self.registry.remove_participant(client_id)

    def handle_client_message(
        self,
        client_id: str,
        message: ClientToServerMessage,
        *,
        reply_target_client_id: str | None = None,
    ) -> str | None:
        reply_target = client_id if reply_target_client_id is None else reply_target_client_id
        try:
            if isinstance(message, JoinLobby):
                return self._handle_join_lobby(client_id, message)
            if isinstance(message, SetDisplayName):
                self._handle_set_display_name(client_id, message)
                return None
            if isinstance(message, AssignSeatToClient):
                self._handle_assign_seat(message)
                return None
            if isinstance(message, CreateLocalBotOnSeat):
                self._handle_create_local_bot(message)
                return None
            if isinstance(message, ClearSeat):
                self._handle_clear_seat(message)
                return None
            if isinstance(message, RequestStartGame):
                self._handle_start_game()
                return None
            if isinstance(message, (SubmitCard, SubmitRowChoice)):
                self._forward_game_message(client_id, message)
                return None
            raise TypeError(f"unsupported client message type: {type(message)!r}")
        except Exception as exc:
            self.outbox.append(OutgoingEnvelope(LobbyActionRejected(message=str(exc)), target_client_id=reply_target))
            if self.active_match is None:
                self.outbox.append(
                    OutgoingEnvelope(
                        build_lobby_state_updated(self.lobby_state, self.registry, self._pending_bot_display_names()),
                        target_client_id=reply_target,
                    )
                )
            return None

    def drain_outbox(self) -> list[OutgoingEnvelope]:
        drained = list(self.outbox)
        self.outbox.clear()
        return drained

    def build_public_state(self) -> PublicState:
        if self.active_match is None:
            raise ValueError("no active match")
        return self.active_match.build_public_state()

    @property
    def state(self) -> GameState:
        if self.active_match is None:
            raise ValueError("no active match")
        return self.active_match.state

    def _handle_join_lobby(self, client_id: str, message: JoinLobby) -> str | None:
        if message.requested_client_id is not None:
            if self.active_match is not None:
                raise ValueError("cannot join after game start")
            requested_client_id = message.requested_client_id.strip()
            pending = self._pending_bot_starts.get(requested_client_id)
            if pending is None:
                raise ValueError("unexpected requested client id")
            self.registry.register_participant(
                Participant(
                    client_id=requested_client_id,
                    display_name=pending.display_name,
                    kind=ParticipantKind.BOT,
                    location=ParticipantLocation.LOCAL,
                )
            )
            self.lobby_state = assign_client_to_seat(self.lobby_state, requested_client_id, pending.seat_index)
            self._pending_bot_starts.pop(requested_client_id, None)
            self._pending_bot_seats.pop(pending.seat_index, None)
            self._running_bot_processes_by_client_id[requested_client_id] = pending.handle
            self._broadcast_lobby_state()
            self._try_finish_start_game()
            return requested_client_id

        if self.active_match is not None or self._start_in_progress:
            raise ValueError("cannot join after game start")
        self.registry.register_participant(
            Participant(
                client_id=client_id,
                display_name=message.display_name.strip(),
                kind=ParticipantKind.HUMAN,
                location=ParticipantLocation.REMOTE,
            )
        )
        self._broadcast_lobby_state()
        return None

    def _handle_set_display_name(self, client_id: str, message: SetDisplayName) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ValueError("cannot change display name after game start")
        self._assert_known_client(client_id)
        self.registry.set_display_name(client_id, message.display_name)
        self._broadcast_lobby_state()

    def _handle_assign_seat(self, message: AssignSeatToClient) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ValueError("cannot edit seats after game start")
        self._assert_known_client(message.target_client_id)
        self._pending_bot_seats.pop(message.seat_index, None)
        self.lobby_state = assign_client_to_seat(self.lobby_state, message.target_client_id, message.seat_index)
        self._broadcast_lobby_state()

    def _handle_create_local_bot(self, message: CreateLocalBotOnSeat) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ValueError("cannot edit seats after game start")
        display_name = self._validate_pending_bot_display_name(message.display_name)
        current_occupant = self.lobby_state.occupant_client_id_for_seat(message.seat_index)
        if current_occupant is not None:
            self.lobby_state = clear_seat(self.lobby_state, message.seat_index)
        self._pending_bot_seats[message.seat_index] = PendingBotSpec(
            seat_index=message.seat_index,
            display_name=display_name,
            seed=self.rng.randrange(2**63),
        )
        self._broadcast_lobby_state()

    def _handle_clear_seat(self, message: ClearSeat) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ValueError("cannot edit seats after game start")
        self._pending_bot_seats.pop(message.seat_index, None)
        self.lobby_state = clear_seat(self.lobby_state, message.seat_index)
        self._broadcast_lobby_state()

    def _handle_start_game(self) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ValueError("game already started")
        if not self._can_start_game_with_pending_bots():
            raise ValueError("cannot start game without full valid lobby configuration")
        if not self._pending_bot_seats:
            self._start_match_now()
            return
        if self.server_handle is None:
            raise ValueError("cannot start local bots without server handle")
        self._start_in_progress = True
        for seat_index, spec in sorted(self._pending_bot_seats.items()):
            client_id = self._next_bot_client_id()
            handle = self.server_handle.spawn_local_bot(
                display_name=spec.display_name,
                client_id=client_id,
                seed=spec.seed,
            )
            self._pending_bot_starts[client_id] = PendingBotStart(
                client_id=client_id,
                seat_index=seat_index,
                display_name=spec.display_name,
                handle=handle,
            )
        self._try_finish_start_game()

    def _try_finish_start_game(self) -> None:
        if not self._start_in_progress:
            return
        if self._pending_bot_starts:
            return
        self._start_match_now()

    def _start_match_now(self) -> None:
        self.lobby_state = mark_game_started(self.lobby_state)
        self._start_in_progress = False
        self.outbox.append(
            OutgoingEnvelope(
                GameStarting(
                    lobby=build_lobby_view(
                        self.lobby_state,
                        self.registry,
                        self._pending_bot_display_names(),
                    )
                )
            )
        )
        match_participants = build_match_participants(self.lobby_state)
        display_names = [
            self.registry.get_participant(client_id).display_name
            for client_id in match_participants.ordered_client_ids
        ]
        state = setup_game(display_names, rng=self.rng)
        self.active_match = MatchHub(state=state)
        self.player_to_client_id = dict(match_participants.player_to_client_id)
        self.client_to_player_id = dict(match_participants.client_to_player_id)
        self.active_match.start_match()
        self._drive_match_until_idle()

    def _forward_game_message(self, client_id: str, message: SubmitCard | SubmitRowChoice) -> None:
        if self.active_match is None:
            raise ValueError("game message received before game start")
        expected_player_id = self.client_to_player_id.get(client_id)
        if expected_player_id is None:
            raise ValueError("client is not assigned to a player")
        if message.player_id != expected_player_id:
            raise ValueError("client may only act for its assigned player")
        self.active_match.handle_client_message(message)
        self._drive_match_until_idle()

    def _drive_match_until_idle(self) -> None:
        if self.active_match is None:
            return
        while True:
            routed_any = self._route_match_messages(self.active_match.drain_outbox())
            if not routed_any:
                return

    def _route_match_messages(self, messages: list[GameServerMessage]) -> bool:
        if not messages:
            return False
        for message in messages:
            self._route_match_message(message)
        return True

    def _route_match_message(self, message: GameServerMessage) -> None:
        if isinstance(message, (ChooseCardRequested, ChooseRowRequested)):
            target_client_id = self.player_to_client_id[message.player_id]
            self.outbox.append(OutgoingEnvelope(message=message, target_client_id=target_client_id))
            return
        self.outbox.append(OutgoingEnvelope(message=message, target_client_id=None))

    def _abort_startup(self) -> None:
        for pending in self._pending_bot_starts.values():
            pending.handle.close()
        self._pending_bot_starts.clear()
        self._start_in_progress = False

    def _broadcast_lobby_state(self) -> None:
        self.outbox.append(
            OutgoingEnvelope(
                build_lobby_state_updated(
                    self.lobby_state,
                    self.registry,
                    self._pending_bot_display_names(),
                ),
                target_client_id=None,
            )
        )

    def _pending_bot_display_names(self) -> dict[int, str]:
        return {
            seat_index: spec.display_name
            for seat_index, spec in self._pending_bot_seats.items()
        }

    def _validate_pending_bot_display_name(self, display_name: str) -> str:
        value = display_name.strip()
        self.registry._validate_display_name(value)
        normalized = value.casefold()
        for spec in self._pending_bot_seats.values():
            if spec.display_name.casefold() == normalized:
                return spec.display_name
        return value

    def _can_start_game_with_pending_bots(self) -> bool:
        if self.lobby_state.game_started:
            return False
        occupied_humans = {seat.seat_index for seat in self.lobby_state.seats if seat.occupant_client_id is not None}
        occupied_pending = set(self._pending_bot_seats)
        occupied = occupied_humans | occupied_pending
        return len(occupied) >= 2 and len(occupied) == self.lobby_state.seat_count

    def _next_bot_client_id(self) -> str:
        while True:
            client_id = f"bot-{self._bot_counter}"
            self._bot_counter += 1
            if (
                not self.registry.has(client_id)
                and client_id not in self._pending_bot_starts
                and client_id not in self._running_bot_processes_by_client_id
            ):
                return client_id

    def _remove_participant(self, client_id: str) -> None:
        self._close_running_bot(client_id)
        self.registry.remove_participant(client_id)
        self.lobby_state = remove_client(self.lobby_state, client_id)

    def _close_running_bot(self, client_id: str) -> None:
        handle = self._running_bot_processes_by_client_id.pop(client_id, None)
        if handle is not None:
            handle.close()

    def _assert_known_client(self, client_id: str) -> None:
        if not self.registry.has(client_id):
            raise ValueError(f"unknown client_id: {client_id!r}")
