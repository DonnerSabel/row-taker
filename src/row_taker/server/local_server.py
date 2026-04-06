from __future__ import annotations

from dataclasses import dataclass, field
import random

from row_taker.clients.random_bot_client import RandomBotClient
from row_taker.engine.game import setup_game
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.state import GameState, PublicState
from row_taker.engine.lobby.config import ClientKind
from row_taker.engine.lobby.rules import (
    can_start_game,
    choose_seat,
    clear_bot_seats,
    fill_empty_seats_with_bots,
    join_lobby,
    leave_seat,
    mark_game_started,
    remove_client,
    set_display_name,
    validate_lobby_state,
)
from row_taker.engine.lobby.state import LobbyState
from row_taker.hub.match_hub import MatchHub
from row_taker.protocol.messages import (
    ChooseCardRequested,
    ChooseRowRequested,
    ChooseSeat,
    ClearBotSeats,
    ClientToServerMessage,
    FillEmptySeatsWithBots,
    GameStarting,
    JoinLobby,
    LeaveSeat,
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
    bot_clients_by_player_id: dict[PlayerID, RandomBotClient] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.lobby_state = LobbyState(seat_count=self.seat_count)

    def register_connection(self, client_id: str) -> None:
        # connection exists but is not in lobby until JoinLobby arrives
        pass

    def disconnect_client(self, client_id: str) -> None:
        self.registry.remove(client_id)
        if self.active_match is None:
            try:
                self.lobby_state = remove_client(self.lobby_state, client_id)
            except Exception:
                return
            self._broadcast_lobby_state()

    def handle_client_message(self, client_id: str, message: ClientToServerMessage) -> None:
        try:
            if isinstance(message, JoinLobby):
                self._handle_join_lobby(client_id, message)
                return
            if isinstance(message, SetDisplayName):
                self._handle_set_display_name(client_id, message)
                return
            if isinstance(message, ChooseSeat):
                self._handle_choose_seat(client_id, message)
                return
            if isinstance(message, LeaveSeat):
                self._handle_leave_seat(client_id)
                return
            if isinstance(message, FillEmptySeatsWithBots):
                self._handle_fill_bots()
                return
            if isinstance(message, ClearBotSeats):
                self._handle_clear_bots()
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
        self.registry.add(client_id, message.display_name)
        self.lobby_state = join_lobby(self.lobby_state, client_id, message.display_name)
        self._broadcast_lobby_state()

    def _handle_set_display_name(self, client_id: str, message: SetDisplayName) -> None:
        if self.active_match is not None:
            raise ValueError('cannot change display name after game start')
        self.registry.set_display_name(client_id, message.display_name)
        self.lobby_state = set_display_name(self.lobby_state, client_id, message.display_name)
        self._broadcast_lobby_state()

    def _handle_choose_seat(self, client_id: str, message: ChooseSeat) -> None:
        if self.active_match is not None:
            raise ValueError('cannot choose seat after game start')
        self.lobby_state = choose_seat(self.lobby_state, client_id, message.seat_index)
        self.registry.set_seat(client_id, message.seat_index)
        self._broadcast_lobby_state()

    def _handle_leave_seat(self, client_id: str) -> None:
        if self.active_match is not None:
            raise ValueError('cannot leave seat after game start')
        self.lobby_state = leave_seat(self.lobby_state, client_id)
        self.registry.set_seat(client_id, None)
        self._broadcast_lobby_state()

    def _handle_fill_bots(self) -> None:
        if self.active_match is not None:
            raise ValueError('cannot add bots after game start')
        self.lobby_state = fill_empty_seats_with_bots(self.lobby_state)
        self._broadcast_lobby_state()

    def _handle_clear_bots(self) -> None:
        if self.active_match is not None:
            raise ValueError('cannot remove bots after game start')
        self.lobby_state = clear_bot_seats(self.lobby_state)
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

    def _build_player_mapping(self, match_config) -> None:
        self.player_to_client_id.clear()
        self.client_to_player_id.clear()
        self.bot_clients_by_player_id.clear()
        for seat in match_config.seats:
            player_id = PlayerID(f'player-{seat.seat_index}')
            if seat.kind == ClientKind.HUMAN:
                matching_seat = self.lobby_state.seats[seat.seat_index]
                if matching_seat.client_id is None:
                    raise ValueError('human seat missing client mapping')
                self.player_to_client_id[player_id] = matching_seat.client_id
                self.client_to_player_id[matching_seat.client_id] = player_id
            else:
                self.bot_clients_by_player_id[player_id] = RandomBotClient(rng=self.rng)

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
                    bot_client = self.bot_clients_by_player_id.get(message.player_id)
                    if bot_client is not None:
                        response = bot_client.handle_server_message(message)
                        if response is not None:
                            self.active_match.handle_client_message(response)
                            follow_up.extend(self.active_match.drain_outbox())
                        continue
                    target_client_id = self.player_to_client_id[message.player_id]
                    self.outbox.append(OutgoingEnvelope(message=message, target_client_id=target_client_id))
                    continue
                if isinstance(message, (StateUpdated, TrickResolved)):
                    self.outbox.append(OutgoingEnvelope(message=message, target_client_id=None))
                    continue
                self.outbox.append(OutgoingEnvelope(message=message, target_client_id=None))
            pending = follow_up

    def _broadcast_lobby_state(self) -> None:
        validate_lobby_state(self.lobby_state)
        self.outbox.append(OutgoingEnvelope(LobbyStateUpdated(lobby_state=self.lobby_state), target_client_id=None))
