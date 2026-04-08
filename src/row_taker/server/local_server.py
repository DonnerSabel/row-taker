from __future__ import annotations

from dataclasses import dataclass, field
import random

from row_taker.clients.random_bot_client import RandomBotClient
from row_taker.engine.game import setup_game
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.state import GameState, PublicState
from row_taker.engine.lobby.rules import assign_client_to_seat, can_start_game, clear_seat, mark_game_started, remove_client
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
from row_taker.server.client_registry import ClientRegistry
from row_taker.server.lobby_view import build_lobby_state_updated, build_lobby_view
from row_taker.server.match_participants import build_match_participants
from row_taker.server.participants import Participant, ParticipantKind, ParticipantLocation


@dataclass(slots=True, frozen=True)
class OutgoingEnvelope:
    message: ServerToClientMessage
    target_client_id: str | None = None


@dataclass(slots=True)
class LocalServer:
    rng: random.Random
    seat_count: int = 4
    lobby_state: LobbyState = field(default_factory=LobbyState)
    active_match: MatchHub | None = None
    outbox: list[OutgoingEnvelope] = field(default_factory=list)
    registry: ClientRegistry = field(default_factory=ClientRegistry)
    player_to_client_id: dict[PlayerID, str] = field(default_factory=dict)
    client_to_player_id: dict[str, PlayerID] = field(default_factory=dict)
    bot_clients_by_client_id: dict[str, RandomBotClient] = field(default_factory=dict)
    _bot_counter: int = 1

    def __post_init__(self) -> None:
        self.lobby_state = LobbyState(seat_count=self.seat_count)

    def register_connection(self, client_id: str) -> None:
        pass

    def disconnect_client(self, client_id: str) -> None:
        if self.registry.has(client_id):
            kind = self.registry.get_participant(client_id).kind
            if self.active_match is None:
                self._remove_participant(client_id)
                self._broadcast_lobby_state()
            elif kind == ParticipantKind.HUMAN:
                # model-level replacement by bot is a later step; for now the active game keeps running only for bots already present
                self.client_to_player_id.pop(client_id, None)
                self.registry.remove_participant(client_id)
            else:
                self.registry.remove_participant(client_id)
        self.bot_clients_by_client_id.pop(client_id, None)

    def handle_client_message(self, client_id: str, message: ClientToServerMessage) -> None:
        try:
            if isinstance(message, JoinLobby):
                self._handle_join_lobby(client_id, message)
                return
            if isinstance(message, SetDisplayName):
                self._handle_set_display_name(client_id, message)
                return
            if isinstance(message, AssignSeatToClient):
                self._handle_assign_seat(message)
                return
            if isinstance(message, CreateLocalBotOnSeat):
                self._handle_create_local_bot(message)
                return
            if isinstance(message, ClearSeat):
                self._handle_clear_seat(message)
                return
            if isinstance(message, RequestStartGame):
                self._handle_start_game()
                return
            if isinstance(message, (SubmitCard, SubmitRowChoice)):
                self._forward_game_message(client_id, message)
                return
            raise TypeError(f'unsupported client message type: {type(message)!r}')
        except Exception as exc:
            self.outbox.append(OutgoingEnvelope(LobbyActionRejected(message=str(exc)), target_client_id=client_id))
            if self.active_match is None:
                self.outbox.append(OutgoingEnvelope(build_lobby_state_updated(self.lobby_state, self.registry), target_client_id=client_id))

    def drain_outbox(self) -> list[OutgoingEnvelope]:
        drained = list(self.outbox)
        self.outbox.clear()
        return drained

    def build_public_state(self) -> PublicState:
        if self.active_match is None:
            raise ValueError('no active match')
        return self.active_match.build_public_state()

    @property
    def state(self) -> GameState:
        if self.active_match is None:
            raise ValueError('no active match')
        return self.active_match.state

    def _handle_join_lobby(self, client_id: str, message: JoinLobby) -> None:
        if self.active_match is not None:
            raise ValueError('cannot join after game start')
        self.registry.register_participant(
            Participant(
                client_id=client_id,
                display_name=message.display_name.strip(),
                kind=ParticipantKind.HUMAN,
                location=ParticipantLocation.REMOTE,
            )
        )
        self._broadcast_lobby_state()

    def _handle_set_display_name(self, client_id: str, message: SetDisplayName) -> None:
        if self.active_match is not None:
            raise ValueError('cannot change display name after game start')
        self._assert_known_client(client_id)
        self.registry.set_display_name(client_id, message.display_name)
        self._broadcast_lobby_state()

    def _handle_assign_seat(self, message: AssignSeatToClient) -> None:
        if self.active_match is not None:
            raise ValueError('cannot edit seats after game start')
        self._assert_known_client(message.target_client_id)
        previous_client_id = self.lobby_state.occupant_client_id_for_seat(message.seat_index)
        self.lobby_state = assign_client_to_seat(self.lobby_state, message.target_client_id, message.seat_index)
        if previous_client_id is not None and previous_client_id != message.target_client_id:
            previous_participant = self.registry.get_participant(previous_client_id)
            if previous_participant.kind == ParticipantKind.BOT:
                self._remove_participant(previous_client_id)
        self._broadcast_lobby_state()

    def _handle_create_local_bot(self, message: CreateLocalBotOnSeat) -> None:
        if self.active_match is not None:
            raise ValueError('cannot edit seats after game start')
        previous_client_id = self.lobby_state.occupant_client_id_for_seat(message.seat_index)
        if previous_client_id is not None:
            previous_participant = self.registry.get_participant(previous_client_id)
            if previous_participant.kind == ParticipantKind.BOT:
                self.registry.set_display_name(previous_client_id, message.display_name)
                self._broadcast_lobby_state()
                return

        bot_client_id = self._next_bot_client_id()
        self.registry.register_participant(
            Participant(
                client_id=bot_client_id,
                display_name=message.display_name.strip(),
                kind=ParticipantKind.BOT,
                location=ParticipantLocation.LOCAL,
            ),
            controller=RandomBotClient(rng=self.rng),
        )
        self.lobby_state = assign_client_to_seat(self.lobby_state, bot_client_id, message.seat_index)
        if previous_client_id is not None:
            previous_participant = self.registry.get_participant(previous_client_id)
            if previous_participant.kind == ParticipantKind.BOT:
                self._remove_participant(previous_client_id)
        self._broadcast_lobby_state()

    def _handle_clear_seat(self, message: ClearSeat) -> None:
        if self.active_match is not None:
            raise ValueError('cannot edit seats after game start')
        previous_client_id = self.lobby_state.occupant_client_id_for_seat(message.seat_index)
        self.lobby_state = clear_seat(self.lobby_state, message.seat_index)
        if previous_client_id is not None:
            previous_participant = self.registry.get_participant(previous_client_id)
            if previous_participant.kind == ParticipantKind.BOT:
                self._remove_participant(previous_client_id)
        self._broadcast_lobby_state()

    def _handle_start_game(self) -> None:
        if self.active_match is not None:
            raise ValueError('game already started')
        if not can_start_game(self.lobby_state):
            raise ValueError('cannot start game without full valid lobby configuration')
        self.lobby_state = mark_game_started(self.lobby_state)
        self.outbox.append(OutgoingEnvelope(GameStarting(lobby=build_lobby_view(self.lobby_state, self.registry))))
        match_participants = build_match_participants(self.lobby_state)
        display_names = [self.registry.get_participant(client_id).display_name for client_id in match_participants.ordered_client_ids]
        state = setup_game(display_names, rng=self.rng)
        self.active_match = MatchHub(state=state)
        self.player_to_client_id = dict(match_participants.player_to_client_id)
        self.client_to_player_id = dict(match_participants.client_to_player_id)
        self.bot_clients_by_client_id = {}
        for client_id in match_participants.ordered_client_ids:
            participant = self.registry.get_participant(client_id)
            if participant.kind == ParticipantKind.BOT:
                controller = self.registry.get_controller(client_id)
                if isinstance(controller, RandomBotClient):
                    self.bot_clients_by_client_id[client_id] = controller
                else:
                    self.bot_clients_by_client_id[client_id] = RandomBotClient(rng=self.rng)
        self.active_match.start_match()
        self._relay_match_messages()

    def _forward_game_message(self, client_id: str, message: SubmitCard | SubmitRowChoice) -> None:
        if self.active_match is None:
            raise ValueError('game message received before game start')
        expected_player_id = self.client_to_player_id.get(client_id)
        if expected_player_id is None:
            raise ValueError('client is not assigned to a human player')
        if message.player_id != expected_player_id:
            raise ValueError('client may only act for its assigned player')
        self.active_match.handle_client_message(message)
        self._relay_match_messages()

    def _relay_match_messages(self) -> None:
        if self.active_match is None:
            return
        pending = self.active_match.drain_outbox()
        while pending:
            follow_up = []
            for message in pending:
                if isinstance(message, (ChooseCardRequested, ChooseRowRequested)):
                    target_client_id = self.player_to_client_id[message.player_id]
                    bot_client = self.bot_clients_by_client_id.get(target_client_id)
                    if bot_client is not None:
                        response = bot_client.handle_server_message(message)
                        if response is not None:
                            self.active_match.handle_client_message(response)
                            follow_up.extend(self.active_match.drain_outbox())
                        continue
                    self.outbox.append(OutgoingEnvelope(message=message, target_client_id=target_client_id))
                    continue
                if isinstance(message, (StateUpdated, TrickResolved)):
                    self.outbox.append(OutgoingEnvelope(message=message, target_client_id=None))
                    continue
                self.outbox.append(OutgoingEnvelope(message=message, target_client_id=None))
            pending = follow_up

    def _broadcast_lobby_state(self) -> None:
        self.outbox.append(OutgoingEnvelope(build_lobby_state_updated(self.lobby_state, self.registry), target_client_id=None))

    def _next_bot_client_id(self) -> str:
        while True:
            client_id = f'bot-{self._bot_counter}'
            self._bot_counter += 1
            if not self.registry.has(client_id):
                return client_id

    def _remove_participant(self, client_id: str) -> None:
        self.registry.remove_participant(client_id)
        self.bot_clients_by_client_id.pop(client_id, None)
        self.lobby_state = remove_client(self.lobby_state, client_id)

    def _assert_known_client(self, client_id: str) -> None:
        if not self.registry.has(client_id):
            raise ValueError(f'unknown client_id: {client_id!r}')
