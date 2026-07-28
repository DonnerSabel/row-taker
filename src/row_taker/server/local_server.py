from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field, replace

from row_taker.engine.game import setup_game
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.phases import Phase
from row_taker.engine.game.player_state_ops import (
    validate_submit_card,
    validate_submit_row_choice,
)
from row_taker.engine.game.state import GameState, PublicState
from row_taker.engine.lobby.rules import (
    assign_client_to_seat,
    clear_seat,
    mark_game_started,
    remove_client,
)
from row_taker.engine.lobby.state import LobbyState
from row_taker.hub.match_hub import MatchHub
from row_taker.protocol.messages import (
    AssignSeatToClient,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameServerMessage,
    GameStarting,
    JoinLobby,
    LeaveSession,
    LobbyActionRejected,
    RequestStartGame,
    ServerToClientMessage,
    SessionEnded,
    SessionEndReason,
    SetDisplayName,
    SubmitCard,
    SubmitRowChoice,
)
from row_taker.server.bot_process_handle import BotProcessHandle
from row_taker.server.client_registry import ClientRegistry
from row_taker.server.errors import ClientRequestRejected
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


logger = logging.getLogger("row_taker.server.local")


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
    _connection_endpoints: dict[str, str | None] = field(default_factory=dict)
    _next_game_revision: int = 1
    _match_abort_in_progress: bool = False
    _session_ended: bool = False

    def __post_init__(self) -> None:
        self.lobby_state = LobbyState(seat_count=self.seat_count)

    def register_connection(self, client_id: str, endpoint_display: str | None = None) -> None:
        self._connection_endpoints[client_id] = endpoint_display

    def disconnect_client(self, client_id: str) -> None:
        endpoint = self._connection_endpoints.pop(client_id, None)
        self._handle_departure(
            client_id,
            reason=SessionEndReason.DISCONNECT,
            endpoint_display=endpoint,
        )

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
            if isinstance(message, LeaveSession):
                self._handle_departure(client_id, reason=SessionEndReason.QUIT)
                return None
            if isinstance(message, SubmitCard | SubmitRowChoice):
                self._forward_game_message(client_id, message)
                return None
            raise TypeError(f"unsupported client message type: {type(message)!r}")
        except ClientRequestRejected as exc:
            self._reject_client_request(reply_target, str(exc))
            return None

    def _reject_client_request(self, target_client_id: str, message: str) -> None:
        self.outbox.append(
            OutgoingEnvelope(
                LobbyActionRejected(message=message),
                target_client_id=target_client_id,
            )
        )
        if self.active_match is None:
            self.outbox.append(
                OutgoingEnvelope(
                    build_lobby_state_updated(
                        self.lobby_state,
                        self.registry,
                        self._pending_bot_display_names(),
                        server_endpoint=self._server_endpoint_display(),
                    ),
                    target_client_id=target_client_id,
                )
            )

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
                raise ClientRequestRejected("cannot join after game start")
            requested_client_id = message.requested_client_id.strip()
            pending = self._pending_bot_starts.get(requested_client_id)
            if pending is None:
                raise ClientRequestRejected("unexpected requested client id")
            endpoint_display = self._connection_endpoints.pop(client_id, None)
            self._connection_endpoints[requested_client_id] = endpoint_display
            self.registry.register_participant(
                Participant(
                    client_id=requested_client_id,
                    display_name=pending.display_name,
                    kind=ParticipantKind.BOT,
                    location=ParticipantLocation.LOCAL,
                    endpoint_display=endpoint_display,
                )
            )
            self.lobby_state = assign_client_to_seat(
                self.lobby_state, requested_client_id, pending.seat_index
            )
            self._pending_bot_starts.pop(requested_client_id, None)
            self._pending_bot_seats.pop(pending.seat_index, None)
            self._running_bot_processes_by_client_id[requested_client_id] = pending.handle
            self._log(
                f"bot joined: client_id={requested_client_id} name={pending.display_name!r} endpoint={endpoint_display or '-'} seat={pending.seat_index}"
            )
            self._broadcast_lobby_state()
            self._try_finish_start_game()
            return requested_client_id

        if self.active_match is not None or self._start_in_progress:
            raise ClientRequestRejected("cannot join after game start")
        display_name = message.display_name.strip()
        self.registry.register_participant(
            Participant(
                client_id=client_id,
                display_name=display_name,
                kind=ParticipantKind.HUMAN,
                location=ParticipantLocation.REMOTE,
                endpoint_display=self._connection_endpoints.get(client_id),
            )
        )
        self._log(
            f"participant joined: client_id={client_id} name={display_name!r} endpoint={self._connection_endpoints.get(client_id) or '-'}"
        )
        self._broadcast_lobby_state()
        return None

    def _handle_set_display_name(self, client_id: str, message: SetDisplayName) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ClientRequestRejected("cannot change display name after game start")
        self._assert_known_client(client_id)
        old_name = self.registry.get_participant(client_id).display_name
        self.registry.set_display_name(client_id, message.display_name)
        new_name = self.registry.get_participant(client_id).display_name
        self._log(
            f"display name changed: client_id={client_id} old={old_name!r} new={new_name!r}"
        )
        self._broadcast_lobby_state()

    def _handle_assign_seat(self, message: AssignSeatToClient) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ClientRequestRejected("cannot edit seats after game start")
        self._validate_seat_index(message.seat_index)
        self._assert_known_client(message.target_client_id)
        self._pending_bot_seats.pop(message.seat_index, None)
        self.lobby_state = assign_client_to_seat(
            self.lobby_state, message.target_client_id, message.seat_index
        )
        self._log(
            f"seat assigned: seat={message.seat_index} client_id={message.target_client_id}"
        )
        self._broadcast_lobby_state()

    def _handle_create_local_bot(self, message: CreateLocalBotOnSeat) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ClientRequestRejected("cannot edit seats after game start")
        self._validate_seat_index(message.seat_index)
        display_name = self._validate_pending_bot_display_name(message.display_name)
        current_occupant = self.lobby_state.occupant_client_id_for_seat(message.seat_index)
        if current_occupant is not None:
            self.lobby_state = clear_seat(self.lobby_state, message.seat_index)
        self._pending_bot_seats[message.seat_index] = PendingBotSpec(
            seat_index=message.seat_index,
            display_name=display_name,
            seed=self.rng.randrange(2**63),
        )
        self._log(
            f"pending bot configured: seat={message.seat_index} name={display_name!r}"
        )
        self._broadcast_lobby_state()

    def _handle_clear_seat(self, message: ClearSeat) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ClientRequestRejected("cannot edit seats after game start")
        self._validate_seat_index(message.seat_index)
        self._pending_bot_seats.pop(message.seat_index, None)
        self.lobby_state = clear_seat(self.lobby_state, message.seat_index)
        self._log(f"seat cleared: seat={message.seat_index}")
        self._broadcast_lobby_state()

    def _handle_start_game(self) -> None:
        if self.active_match is not None or self._start_in_progress:
            raise ClientRequestRejected("game already started")
        if not self._can_start_game_with_pending_bots():
            raise ClientRequestRejected("cannot start game without full valid lobby configuration")
        if not self._pending_bot_seats:
            self._start_match_now()
            return
        if self.server_handle is None:
            raise ClientRequestRejected("cannot start local bots without server handle")
        self._start_in_progress = True
        self._log("starting game: spawning pending local bots")
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
        lobby_view = build_lobby_view(
            self.lobby_state,
            self.registry,
            self._pending_bot_display_names(),
            server_endpoint=self._server_endpoint_display(),
        )
        self.outbox.append(OutgoingEnvelope(GameStarting(lobby=lobby_view)))
        match_participants = build_match_participants(self.lobby_state)
        display_names = [
            self.registry.get_participant(client_id).display_name
            for client_id in match_participants.ordered_client_ids
        ]
        self._log(f"match started: players={display_names!r}")
        state = setup_game(display_names, rng=self.rng)
        self.active_match = MatchHub(state=state)
        self.player_to_client_id = dict(match_participants.player_to_client_id)
        self.client_to_player_id = dict(match_participants.client_to_player_id)
        self.active_match.start_match()
        self._drive_match_until_idle()

    def _forward_game_message(self, client_id: str, message: SubmitCard | SubmitRowChoice) -> None:
        if self.active_match is None:
            raise ClientRequestRejected("game message received before game start")
        expected_player_id = self.client_to_player_id.get(client_id)
        if expected_player_id is None:
            raise ClientRequestRejected("client is not assigned to a player")
        self._validate_game_message(expected_player_id, message)
        self.active_match.handle_client_message(expected_player_id, message)
        self._drive_match_until_idle()

    def _validate_game_message(
        self,
        player_id: PlayerID,
        message: SubmitCard | SubmitRowChoice,
    ) -> None:
        if self.active_match is None:
            raise RuntimeError("cannot validate a game message without an active match")

        player_state = self.active_match.build_player_state_for(player_id)
        try:
            if isinstance(message, SubmitCard):
                player_state.validate_phase(Phase.CHOOSE_CARD)
                if player_id in self.active_match.state.selected_cards:
                    raise ValueError(f"player {player_id!r} has already selected a card")
                validate_submit_card(player_state, message.card_value)
                return

            player_state.validate_phase(Phase.CHOOSE_ROW)
            if player_state.phase_info.active_player_id != player_id:
                raise ValueError(
                    "row choice requested for a different active player"
                )
            validate_submit_row_choice(player_state, message.row_id)
        except ValueError as exc:
            raise ClientRequestRejected(str(exc)) from exc

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
        stamped_message = self._stamp_game_message_revision(message)
        if isinstance(stamped_message, ChooseCardRequested | ChooseRowRequested):
            target_client_id = self.player_to_client_id[stamped_message.player_id]
            logger.debug("route match message: type=%s revision=%s target_client_id=%s", type(stamped_message).__name__, getattr(stamped_message, "revision", None), target_client_id)
            self.outbox.append(OutgoingEnvelope(message=stamped_message, target_client_id=target_client_id))
            return
        logger.debug("route broadcast match message: type=%s revision=%s", type(stamped_message).__name__, getattr(stamped_message, "revision", None))
        self.outbox.append(OutgoingEnvelope(message=stamped_message, target_client_id=None))

    def _stamp_game_message_revision(self, message: GameServerMessage) -> GameServerMessage:
        revision = self._next_game_revision
        self._next_game_revision += 1
        return replace(message, revision=revision)

    def _handle_departure(
        self,
        client_id: str,
        *,
        reason: SessionEndReason,
        endpoint_display: str | None = None,
    ) -> None:
        if not self.registry.has(client_id):
            return
        participant = self.registry.get_participant(client_id)
        endpoint = endpoint_display or participant.endpoint_display or self._connection_endpoints.get(client_id)
        self._log(
            f"participant departed: client_id={client_id} name={participant.display_name!r} reason={reason.value} endpoint={endpoint or '-'}"
        )
        if self.active_match is None:
            self._remove_participant(client_id)
            self._connection_endpoints.pop(client_id, None)
            if self._start_in_progress and participant.kind == ParticipantKind.BOT:
                self._abort_startup()
            if self._match_abort_in_progress:
                if not self.registry.records:
                    self._match_abort_in_progress = False
                return
            self._broadcast_lobby_state()
            return

        if participant.kind == ParticipantKind.HUMAN:
            self._abort_active_match(
                departing_client_id=client_id,
                departing_display_name=participant.display_name,
                reason=reason,
                endpoint_display=endpoint,
            )
            return

        self._close_running_bot(client_id)
        self.registry.remove_participant(client_id)
        self._abort_active_match(
            departing_client_id=client_id,
            departing_display_name=participant.display_name,
            reason=reason,
            endpoint_display=endpoint,
        )

    def _abort_startup(self) -> None:
        for pending in self._pending_bot_starts.values():
            pending.handle.close()
        self._pending_bot_starts.clear()
        self._start_in_progress = False
        self._log("startup aborted")

    def _abort_active_match(
        self,
        *,
        departing_client_id: str,
        departing_display_name: str,
        reason: SessionEndReason,
        endpoint_display: str | None,
    ) -> None:
        message = self._build_session_end_message(
            departing_display_name=departing_display_name,
            reason=reason,
            endpoint_display=endpoint_display,
        )
        remaining_client_ids = [
            client_id for client_id in self.registry.records if client_id != departing_client_id
        ]
        self._log(
            f"active match aborted: client_id={departing_client_id} name={departing_display_name!r} reason={reason.value} remaining_clients={remaining_client_ids!r}"
        )
        logger.debug("abort enqueue start: departing_client_id=%s remaining_clients=%s outbox_before=%s", departing_client_id, remaining_client_ids, len(self.outbox))
        for client_id in remaining_client_ids:
            logger.debug("enqueue SessionEnded: target_client_id=%s reason=%s", client_id, reason.value)
            self.outbox.append(
                OutgoingEnvelope(
                    SessionEnded(
                        message=message,
                        reason=reason,
                        client_id=departing_client_id,
                        display_name=departing_display_name,
                    ),
                    target_client_id=client_id,
                )
            )

        self._match_abort_in_progress = True
        self._session_ended = True
        logger.debug("match abort flagged in progress: departing_client_id=%s", departing_client_id)
        logger.debug("session ended flagged: reason=%s departing_client_id=%s", reason.value, departing_client_id)
        logger.debug("removing departing participant during abort: client_id=%s", departing_client_id)
        self._remove_participant(departing_client_id)
        self._connection_endpoints.pop(departing_client_id, None)

        logger.debug("clearing active match after abort: player_to_client=%s client_to_player=%s", self.player_to_client_id, self.client_to_player_id)
        self.active_match = None
        self.player_to_client_id.clear()
        self.client_to_player_id.clear()
        self.lobby_state = LobbyState(
            seat_count=self.lobby_state.seat_count,
            seats=self.lobby_state.seats,
            game_started=False,
        )

    @property
    def should_shutdown(self) -> bool:
        return (
            self._session_ended
            and self.active_match is None
            and not self._start_in_progress
            and not self.registry.records
            and not self._pending_bot_starts
            and not self._running_bot_processes_by_client_id
        )

    def _server_endpoint_display(self) -> str | None:
        if self.server_handle is None:
            return None
        host = getattr(self.server_handle, "host", None)
        port = getattr(self.server_handle, "port", None)
        if host is None or port is None:
            return None
        return f"{host}:{port}"

    def _broadcast_lobby_state(self) -> None:
        self.outbox.append(
            OutgoingEnvelope(
                build_lobby_state_updated(
                    self.lobby_state,
                    self.registry,
                    self._pending_bot_display_names(),
                    server_endpoint=self._server_endpoint_display(),
                ),
                target_client_id=None,
            )
        )

    def _pending_bot_display_names(self) -> dict[int, str]:
        return {
            seat_index: spec.display_name for seat_index, spec in self._pending_bot_seats.items()
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
        occupied_humans = {
            seat.seat_index
            for seat in self.lobby_state.seats
            if seat.occupant_client_id is not None
        }
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
        logger.debug("remove participant: client_id=%s kind=%s", client_id, self.registry.get_participant(client_id).kind if self.registry.has(client_id) else None)
        self._close_running_bot(client_id)
        self.registry.remove_participant(client_id)
        self.lobby_state = remove_client(self.lobby_state, client_id)

    def _close_running_bot(self, client_id: str) -> None:
        handle = self._running_bot_processes_by_client_id.pop(client_id, None)
        if handle is not None:
            logger.debug("closing running bot process: client_id=%s", client_id)
            handle.close()
            logger.debug("closed running bot process: client_id=%s returncode=%s", client_id, handle.poll())

    def _validate_seat_index(self, seat_index: int) -> None:
        if not 0 <= seat_index < self.lobby_state.seat_count:
            raise ClientRequestRejected(f"seat index out of range: {seat_index}")

    def _assert_known_client(self, client_id: str) -> None:
        if not self.registry.has(client_id):
            raise ClientRequestRejected(f"unknown client_id: {client_id!r}")

    def _build_session_end_message(
        self,
        *,
        departing_display_name: str,
        reason: SessionEndReason,
        endpoint_display: str | None,
    ) -> str:
        if reason is SessionEndReason.QUIT:
            return f"Spiel abgebrochen: {departing_display_name} hat die Sitzung verlassen."
        if reason is SessionEndReason.KICKED:
            return f"Spiel abgebrochen: {departing_display_name} wurde aus der Sitzung entfernt."
        endpoint_suffix = f" ({endpoint_display})" if endpoint_display else ""
        return f"Spiel abgebrochen: Verbindung zu {departing_display_name}{endpoint_suffix} verloren."

    def _log(self, message: str) -> None:
        logger.info(message)
