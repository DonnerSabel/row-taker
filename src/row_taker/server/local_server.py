from __future__ import annotations

from dataclasses import dataclass, field
import random

from row_taker.clients.random_bot_client import RandomBotClient
from row_taker.engine.game import setup_game
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.state import GameState, PublicState
from row_taker.engine.lobby.config import ClientKind, MatchConfig
from row_taker.engine.lobby.rules import (
    add_local_bot,
    assign_client_to_seat,
    can_start_game,
    clear_seat,
    join_lobby,
    mark_game_started,
    remove_client,
    set_display_name,
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
    GameStarting,
    JoinLobby,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    ServerToClientMessage,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    TrickResolved,
)
from row_taker.server.client_registry import ClientRegistry


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
            kind = self.registry.get(client_id).kind
            self.registry.remove(client_id)
            if self.active_match is None:
                try:
                    self.lobby_state = remove_client(self.lobby_state, client_id)
                except Exception:
                    return
                self._broadcast_lobby_state()
            elif kind == ClientKind.HUMAN:
                # model-level replacement by bot is a later step; for now the active game keeps running only for bots already present
                self.client_to_player_id.pop(client_id, None)
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
                self.outbox.append(OutgoingEnvelope(LobbyStateUpdated(lobby_state=self.lobby_state), target_client_id=client_id))

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
        self.registry.add(client_id, message.display_name, ClientKind.HUMAN)
        self.lobby_state = join_lobby(self.lobby_state, client_id, message.display_name)
        self._broadcast_lobby_state()

    def _handle_set_display_name(self, client_id: str, message: SetDisplayName) -> None:
        if self.active_match is not None:
            raise ValueError('cannot change display name after game start')
        self.registry.set_display_name(client_id, message.display_name)
        self.lobby_state = set_display_name(self.lobby_state, client_id, message.display_name)
        self._broadcast_lobby_state()

    def _handle_assign_seat(self, message: AssignSeatToClient) -> None:
        if self.active_match is not None:
            raise ValueError('cannot edit seats after game start')
        self._assert_known_client(message.target_client_id)
        previous = self.lobby_state.occupant_for_seat(message.seat_index)
        self.lobby_state = assign_client_to_seat(self.lobby_state, message.target_client_id, message.seat_index)
        if previous is not None and previous.kind == ClientKind.RANDOM_BOT and previous.client_id != message.target_client_id:
            self._remove_bot_participant(previous.client_id)
        self._broadcast_lobby_state()

    def _handle_create_local_bot(self, message: CreateLocalBotOnSeat) -> None:
        if self.active_match is not None:
            raise ValueError('cannot edit seats after game start')
        previous = self.lobby_state.occupant_for_seat(message.seat_index)
        if previous is not None and previous.kind == ClientKind.RANDOM_BOT:
            self.registry.set_display_name(previous.client_id, message.display_name)
            self.lobby_state = set_display_name(self.lobby_state, previous.client_id, message.display_name)
            self._broadcast_lobby_state()
            return
        bot_client_id = self._next_bot_client_id()
        self.registry.add(bot_client_id, message.display_name, ClientKind.RANDOM_BOT)
        self.lobby_state = add_local_bot(self.lobby_state, bot_client_id, message.display_name)
        self.lobby_state = assign_client_to_seat(self.lobby_state, bot_client_id, message.seat_index)
        if previous is not None and previous.kind == ClientKind.RANDOM_BOT:
            self._remove_bot_participant(previous.client_id)
        self._broadcast_lobby_state()

    def _handle_clear_seat(self, message: ClearSeat) -> None:
        if self.active_match is not None:
            raise ValueError('cannot edit seats after game start')
        previous = self.lobby_state.occupant_for_seat(message.seat_index)
        self.lobby_state = clear_seat(self.lobby_state, message.seat_index)
        if previous is not None and previous.kind == ClientKind.RANDOM_BOT:
            self._remove_bot_participant(previous.client_id)
        self._broadcast_lobby_state()

    def _handle_start_game(self) -> None:
        if self.active_match is not None:
            raise ValueError('game already started')
        if not can_start_game(self.lobby_state):
            raise ValueError('cannot start game without full valid lobby configuration')
        self.lobby_state = mark_game_started(self.lobby_state)
        self.outbox.append(OutgoingEnvelope(GameStarting(lobby_state=self.lobby_state)))
        match_config = self.lobby_state.to_match_config()
        state = setup_game([seat.name for seat in match_config.seats], rng=self.rng)
        self.active_match = MatchHub(state=state)
        self._build_player_mapping(match_config)
        self.active_match.start_match()
        self._relay_match_messages()

    def _build_player_mapping(self, match_config: MatchConfig) -> None:
        self.player_to_client_id.clear()
        self.client_to_player_id.clear()
        self.bot_clients_by_client_id.clear()
        for seat in match_config.seats:
            player_id = PlayerID(f'player-{seat.seat_index}')
            occupant = self.lobby_state.occupant_for_seat(seat.seat_index)
            if occupant is None:
                raise ValueError('seat missing occupant at match start')
            client_id = occupant.client_id
            self.player_to_client_id[player_id] = client_id
            self.client_to_player_id[client_id] = player_id
            if occupant.kind == ClientKind.RANDOM_BOT:
                self.bot_clients_by_client_id[client_id] = RandomBotClient(rng=self.rng)

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
        self.outbox.append(OutgoingEnvelope(LobbyStateUpdated(lobby_state=self.lobby_state), target_client_id=None))

    def _next_bot_client_id(self) -> str:
        while True:
            client_id = f'bot-{self._bot_counter}'
            self._bot_counter += 1
            if not self.registry.has(client_id):
                return client_id

    def _remove_bot_participant(self, client_id: str) -> None:
        self.registry.remove(client_id)
        self.lobby_state = remove_client(self.lobby_state, client_id)

    def _assert_known_client(self, client_id: str) -> None:
        if not self.registry.has(client_id):
            raise ValueError(f'unknown client_id: {client_id!r}')
