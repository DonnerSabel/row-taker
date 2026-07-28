from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

from row_taker.engine.game import setup_game
from row_taker.engine.game.models import PlayerID
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
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameStarting,
    JoinLobby,
    LeaveSession,
    LobbyActionRejected,
    RequestStartGame,
    SessionEndReason,
    SetDisplayName,
    SubmitCard,
    SubmitRowChoice,
)
from row_taker.server.client_registry import ClientRegistry
from row_taker.server.errors import ClientRequestRejected
from row_taker.server.lobby_view import build_lobby_state_updated, build_lobby_view
from row_taker.server.local_bot_manager import LocalBotManager
from row_taker.server.match_participants import build_match_participants
from row_taker.server.match_session_router import MatchSessionRouter
from row_taker.server.outgoing import OutgoingEnvelope
from row_taker.server.participants import Participant, ParticipantKind, ParticipantLocation
from row_taker.server.server_handle import ServerHandle

logger = logging.getLogger("row_taker.server.local")


@dataclass(slots=True)
class LocalServer:
    rng: random.Random
    seat_count: int = 4
    server_handle: ServerHandle | None = None
    lobby_state: LobbyState = field(default_factory=LobbyState)
    outbox: list[OutgoingEnvelope] = field(default_factory=list)
    registry: ClientRegistry = field(default_factory=ClientRegistry)
    match_router: MatchSessionRouter = field(default_factory=MatchSessionRouter)
    bot_manager: LocalBotManager = field(init=False)
    _start_in_progress: bool = False
    _connection_endpoints: dict[str, str | None] = field(default_factory=dict)
    _match_abort_in_progress: bool = False
    _session_ended: bool = False

    def __post_init__(self) -> None:
        self.lobby_state = LobbyState(seat_count=self.seat_count)
        self.bot_manager = LocalBotManager(rng=self.rng)

    @property
    def active_match(self) -> MatchHub | None:
        return self.match_router.active_match

    @property
    def player_to_client_id(self) -> dict[PlayerID, str]:
        return self.match_router.player_to_client_id

    @property
    def client_to_player_id(self) -> dict[str, PlayerID]:
        return self.match_router.client_to_player_id

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
        if not self.match_router.is_active:
            self.outbox.append(
                OutgoingEnvelope(
                    build_lobby_state_updated(
                        self.lobby_state,
                        self.registry,
                        self.bot_manager.pending_display_names(),
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
        return self.match_router.build_public_state()

    @property
    def state(self) -> GameState:
        return self.match_router.state

    def _handle_join_lobby(self, client_id: str, message: JoinLobby) -> str | None:
        if message.requested_client_id is not None:
            if self.match_router.is_active:
                raise ClientRequestRejected("cannot join after game start")
            requested_client_id = message.requested_client_id.strip()
            pending = self.bot_manager.pending_start(requested_client_id)
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
                self.lobby_state,
                requested_client_id,
                pending.seat_index,
            )
            self.bot_manager.mark_connected(requested_client_id)
            self._log(
                "bot joined: "
                f"client_id={requested_client_id} "
                f"name={pending.display_name!r} "
                f"endpoint={endpoint_display or '-'} "
                f"seat={pending.seat_index}"
            )
            self._broadcast_lobby_state()
            self._try_finish_start_game()
            return requested_client_id

        if self.match_router.is_active or self._start_in_progress:
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
            "participant joined: "
            f"client_id={client_id} "
            f"name={display_name!r} "
            f"endpoint={self._connection_endpoints.get(client_id) or '-'}"
        )
        self._broadcast_lobby_state()
        return None

    def _handle_set_display_name(self, client_id: str, message: SetDisplayName) -> None:
        if self.match_router.is_active or self._start_in_progress:
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
        if self.match_router.is_active or self._start_in_progress:
            raise ClientRequestRejected("cannot edit seats after game start")
        self._validate_seat_index(message.seat_index)
        self._assert_known_client(message.target_client_id)
        self.bot_manager.clear_reservation(message.seat_index)
        self.lobby_state = assign_client_to_seat(
            self.lobby_state,
            message.target_client_id,
            message.seat_index,
        )
        self._log(
            f"seat assigned: seat={message.seat_index} client_id={message.target_client_id}"
        )
        self._broadcast_lobby_state()

    def _handle_create_local_bot(self, message: CreateLocalBotOnSeat) -> None:
        if self.match_router.is_active or self._start_in_progress:
            raise ClientRequestRejected("cannot edit seats after game start")
        self._validate_seat_index(message.seat_index)
        display_name = self._validate_pending_bot_display_name(message.display_name)
        current_occupant = self.lobby_state.occupant_client_id_for_seat(message.seat_index)
        if current_occupant is not None:
            self.lobby_state = clear_seat(self.lobby_state, message.seat_index)
        self.bot_manager.reserve(message.seat_index, display_name)
        self._log(
            f"pending bot configured: seat={message.seat_index} name={display_name!r}"
        )
        self._broadcast_lobby_state()

    def _handle_clear_seat(self, message: ClearSeat) -> None:
        if self.match_router.is_active or self._start_in_progress:
            raise ClientRequestRejected("cannot edit seats after game start")
        self._validate_seat_index(message.seat_index)
        self.bot_manager.clear_reservation(message.seat_index)
        self.lobby_state = clear_seat(self.lobby_state, message.seat_index)
        self._log(f"seat cleared: seat={message.seat_index}")
        self._broadcast_lobby_state()

    def _handle_start_game(self) -> None:
        if self.match_router.is_active or self._start_in_progress:
            raise ClientRequestRejected("game already started")
        if not self.bot_manager.can_complete_lobby(self.lobby_state):
            raise ClientRequestRejected(
                "cannot start game without full valid lobby configuration"
            )
        if not self.bot_manager.has_pending_reservations:
            self._start_match_now()
            return
        if self.server_handle is None:
            raise ClientRequestRejected("cannot start local bots without server handle")
        self._start_in_progress = True
        self._log("starting game: spawning pending local bots")
        self.bot_manager.spawn_pending(
            self.server_handle,
            client_id_in_use=self.registry.has,
        )
        self._try_finish_start_game()

    def _try_finish_start_game(self) -> None:
        if not self._start_in_progress:
            return
        if self.bot_manager.has_pending_starts:
            return
        self._start_match_now()

    def _start_match_now(self) -> None:
        self.lobby_state = mark_game_started(self.lobby_state)
        self._start_in_progress = False
        lobby_view = build_lobby_view(
            self.lobby_state,
            self.registry,
            self.bot_manager.pending_display_names(),
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
        self.match_router.start(state, match_participants)
        self.outbox.extend(self.match_router.drain_outgoing())

    def _forward_game_message(
        self,
        client_id: str,
        message: SubmitCard | SubmitRowChoice,
    ) -> None:
        self.match_router.handle_client_message(client_id, message)
        self.outbox.extend(self.match_router.drain_outgoing())

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
        endpoint = (
            endpoint_display
            or participant.endpoint_display
            or self._connection_endpoints.get(client_id)
        )
        self._log(
            "participant departed: "
            f"client_id={client_id} "
            f"name={participant.display_name!r} "
            f"reason={reason.value} "
            f"endpoint={endpoint or '-'}"
        )
        if not self.match_router.is_active:
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

        self._abort_active_match(
            departing_client_id=client_id,
            departing_display_name=participant.display_name,
            reason=reason,
            endpoint_display=endpoint,
        )

    def _abort_startup(self) -> None:
        self.bot_manager.abort_startup()
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
        remaining_client_ids = tuple(
            client_id
            for client_id in self.registry.records
            if client_id != departing_client_id
        )
        self._log(
            "active match aborted: "
            f"client_id={departing_client_id} "
            f"name={departing_display_name!r} "
            f"reason={reason.value} "
            f"remaining_clients={list(remaining_client_ids)!r}"
        )
        self.match_router.abort(
            departing_client_id=departing_client_id,
            departing_display_name=departing_display_name,
            reason=reason,
            message=message,
            remaining_client_ids=remaining_client_ids,
        )
        self.outbox.extend(self.match_router.drain_outgoing())

        self._match_abort_in_progress = True
        self._session_ended = True
        logger.debug(
            "match abort flagged in progress: departing_client_id=%s",
            departing_client_id,
        )
        self._remove_participant(departing_client_id)
        self._connection_endpoints.pop(departing_client_id, None)
        self.lobby_state = LobbyState(
            seat_count=self.lobby_state.seat_count,
            seats=self.lobby_state.seats,
            game_started=False,
        )

    @property
    def should_shutdown(self) -> bool:
        return (
            self._session_ended
            and not self.match_router.is_active
            and not self._start_in_progress
            and not self.registry.records
            and not self.bot_manager.has_pending_starts
            and not self.bot_manager.has_running_bots
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
                    self.bot_manager.pending_display_names(),
                    server_endpoint=self._server_endpoint_display(),
                )
            )
        )

    def _validate_pending_bot_display_name(self, display_name: str) -> str:
        value = self.registry._validate_display_name(display_name)
        return self.bot_manager.normalize_pending_display_name(value)

    def _remove_participant(self, client_id: str) -> None:
        logger.debug(
            "remove participant: client_id=%s kind=%s",
            client_id,
            self.registry.get_participant(client_id).kind
            if self.registry.has(client_id)
            else None,
        )
        self.bot_manager.close_running(client_id)
        self.registry.remove_participant(client_id)
        self.lobby_state = remove_client(self.lobby_state, client_id)

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
            return (
                f"Spiel abgebrochen: {departing_display_name} wurde aus der Sitzung entfernt."
            )
        endpoint_suffix = f" ({endpoint_display})" if endpoint_display else ""
        return (
            "Spiel abgebrochen: Verbindung zu "
            f"{departing_display_name}{endpoint_suffix} verloren."
        )

    def _log(self, message: str) -> None:
        logger.info(message)
