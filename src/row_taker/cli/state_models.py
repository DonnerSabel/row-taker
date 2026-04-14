from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from row_taker.cli.local_resolution import LocalResolutionState
from row_taker.client.core_state import ClientCoreState, ClientMode, PendingAction, initial_client_core_state
from row_taker.client.presentation_events import PresentationEvent
from row_taker.engine.game.state import PlayerState, PublicState
from row_taker.protocol.messages import CardsRevealed, LobbyView


@dataclass(frozen=True, slots=True)
class UiMessage:
    level: Literal["info", "error"]
    text: str


@dataclass(frozen=True, slots=True)
class LobbyScreen:
    kind: Literal["main", "rename", "seat_edit", "bot_name"]
    seat_index: int | None = None


@dataclass(frozen=True, slots=True)
class GameScreen:
    kind: Literal["waiting", "choose_card", "choose_row", "ended"]
    player_state: PlayerState | None = None


Screen = LobbyScreen | GameScreen


@dataclass(frozen=True, slots=True)
class CliFrontendState:
    screen: Screen = field(default_factory=lambda: LobbyScreen(kind="main"))
    flash_message: UiMessage | None = None
    exit_on_ack: bool = False
    suppress_final_result: bool = False
    should_exit: bool = False


@dataclass(frozen=True, slots=True, init=False)
class CliState:
    core_state: ClientCoreState
    frontend_state: CliFrontendState

    def __init__(
        self,
        *,
        core_state: ClientCoreState | None = None,
        frontend_state: CliFrontendState | None = None,
        own_client_id: str | None = None,
        own_player_id: str | None = None,
        lobby_view: LobbyView | None = None,
        public_state: PublicState | None = None,
        player_state: PlayerState | None = None,
        screen: Screen | None = None,
        flash_message: UiMessage | None = None,
        revealed_trick: CardsRevealed | None = None,
        local_resolution: LocalResolutionState | None = None,
        presentation_events: tuple[PresentationEvent, ...] = (),
        pending_presentation_events: tuple[PresentationEvent, ...] = (),
        received_game_revision: int | None = None,
        applied_game_revision: int | None = None,
        session_error: str | None = None,
        exit_on_ack: bool = False,
        suppress_final_result: bool = False,
        should_exit: bool = False,
        client_mode: ClientMode = ClientMode.LOBBY,
        pending_action: PendingAction = PendingAction.LOBBY_COMMAND,
    ) -> None:
        if core_state is None:
            core_state = ClientCoreState(
                own_client_id=own_client_id,
                own_player_id=own_player_id,
                lobby_view=lobby_view,
                public_state=public_state,
                player_state=player_state,
                session_error=session_error,
                revealed_trick=revealed_trick,
                trick_presentation_state=local_resolution,
                presentation_events=presentation_events,
                pending_presentation_events=pending_presentation_events,
                received_game_revision=received_game_revision,
                applied_game_revision=applied_game_revision,
                client_mode=client_mode,
                pending_action=pending_action,
            )
        if frontend_state is None:
            frontend_state = CliFrontendState(
                screen=LobbyScreen(kind="main") if screen is None else screen,
                flash_message=flash_message,
                exit_on_ack=exit_on_ack,
                suppress_final_result=suppress_final_result,
                should_exit=should_exit,
            )
        object.__setattr__(self, "core_state", core_state)
        object.__setattr__(self, "frontend_state", frontend_state)

    @property
    def own_client_id(self) -> str | None:
        return self.core_state.own_client_id

    @property
    def own_player_id(self) -> str | None:
        return self.core_state.own_player_id

    @property
    def lobby_view(self) -> LobbyView | None:
        return self.core_state.lobby_view

    @property
    def public_state(self) -> PublicState | None:
        return self.core_state.public_state

    @property
    def player_state(self) -> PlayerState | None:
        return self.core_state.player_state

    @property
    def screen(self) -> Screen:
        return self.frontend_state.screen

    @property
    def flash_message(self) -> UiMessage | None:
        return self.frontend_state.flash_message

    @property
    def revealed_trick(self) -> CardsRevealed | None:
        return self.core_state.revealed_trick

    @property
    def local_resolution(self) -> LocalResolutionState | None:
        return self.core_state.trick_presentation_state

    @property
    def presentation_events(self) -> tuple[PresentationEvent, ...]:
        return self.core_state.presentation_events

    @property
    def pending_presentation_events(self) -> tuple[PresentationEvent, ...]:
        return self.core_state.pending_presentation_events

    @property
    def received_game_revision(self) -> int | None:
        return self.core_state.received_game_revision

    @property
    def applied_game_revision(self) -> int | None:
        return self.core_state.applied_game_revision

    @property
    def session_error(self) -> str | None:
        return self.core_state.session_error

    @property
    def exit_on_ack(self) -> bool:
        return self.frontend_state.exit_on_ack

    @property
    def suppress_final_result(self) -> bool:
        return self.frontend_state.suppress_final_result

    @property
    def should_exit(self) -> bool:
        return self.frontend_state.should_exit

    @property
    def client_mode(self) -> ClientMode:
        return self.core_state.client_mode

    @property
    def pending_action(self) -> PendingAction:
        return self.core_state.pending_action


LobbyStateMain = LobbyScreen
LobbyStateRename = LobbyScreen
LobbyStateSeatEdit = LobbyScreen
GameStateWaiting = GameScreen
GameStateChooseCard = GameScreen
GameStateChooseRow = GameScreen
GameStateEnded = GameScreen


def initial_cli_state(own_client_id: str | None = None) -> CliState:
    core = initial_client_core_state(own_client_id=own_client_id)
    return CliState(core_state=core, frontend_state=CliFrontendState())



def has_pending_presentation(state: CliState) -> bool:
    return bool(state.core_state.pending_presentation_events)



def has_visible_presentation(state: CliState) -> bool:
    return bool(state.core_state.presentation_events)



def extract_client_core_state(state: CliState) -> ClientCoreState:
    return state.core_state



def apply_client_core_state(state: CliState, core: ClientCoreState) -> CliState:
    return replace(state, core_state=core)



def apply_frontend_state(state: CliState, frontend: CliFrontendState) -> CliState:
    return replace(state, frontend_state=frontend)
