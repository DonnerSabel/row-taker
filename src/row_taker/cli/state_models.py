from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from row_taker.client.core_state import ClientCoreState, ClientMode, PendingAction, initial_client_core_state
from row_taker.client.presentation_events import PresentationEvent
from row_taker.client.trick_presentation_resolver import TrickPresentationState
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
LobbySubmenu = Literal["main", "rename", "seat_edit", "bot_name"]


@dataclass(frozen=True, slots=True)
class CliNavigationState:
    lobby_submenu: LobbySubmenu = "main"
    selected_seat_index: int | None = None


@dataclass(frozen=True, slots=True)
class CliFeedbackState:
    flash_message: UiMessage | None = None
    exit_on_ack: bool = False
    suppress_final_result: bool = False
    should_exit: bool = False


@dataclass(frozen=True, slots=True)
class CliState:
    core_state: ClientCoreState = field(default_factory=initial_client_core_state)
    navigation_state: CliNavigationState = field(default_factory=CliNavigationState)
    feedback_state: CliFeedbackState = field(default_factory=CliFeedbackState)

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
        return _screen_from_state(self)

    @property
    def flash_message(self) -> UiMessage | None:
        return self.feedback_state.flash_message

    @property
    def revealed_trick(self) -> CardsRevealed | None:
        return self.core_state.revealed_trick

    @property
    def local_resolution(self) -> TrickPresentationState | None:
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
        return self.feedback_state.exit_on_ack

    @property
    def suppress_final_result(self) -> bool:
        return self.feedback_state.suppress_final_result

    @property
    def should_exit(self) -> bool:
        return self.feedback_state.should_exit

    @property
    def client_mode(self) -> ClientMode:
        return self.core_state.client_mode

    @property
    def pending_action(self) -> PendingAction:
        return self.core_state.pending_action


def initial_cli_state(own_client_id: str | None = None) -> CliState:
    return CliState(core_state=initial_client_core_state(own_client_id=own_client_id))


def has_pending_presentation(state: CliState) -> bool:
    return bool(state.core_state.pending_presentation_events)


def has_visible_presentation(state: CliState) -> bool:
    return bool(state.core_state.presentation_events)


def extract_client_core_state(state: CliState) -> ClientCoreState:
    return state.core_state


def apply_client_core_state(state: CliState, core: ClientCoreState) -> CliState:
    return replace(state, core_state=core)


def apply_navigation_state(state: CliState, navigation: CliNavigationState) -> CliState:
    return replace(state, navigation_state=navigation)


def apply_feedback_state(state: CliState, feedback: CliFeedbackState) -> CliState:
    return replace(state, feedback_state=feedback)


def with_core_updates(state: CliState, **changes: object) -> CliState:
    return replace(state, core_state=replace(state.core_state, **changes))


def with_navigation_updates(state: CliState, **changes: object) -> CliState:
    return replace(state, navigation_state=replace(state.navigation_state, **changes))


def with_feedback_updates(state: CliState, **changes: object) -> CliState:
    return replace(state, feedback_state=replace(state.feedback_state, **changes))


def with_screen(state: CliState, screen: Screen) -> CliState:
    if isinstance(screen, LobbyScreen):
        return replace(
            state,
            core_state=replace(
                state.core_state,
                client_mode=ClientMode.LOBBY,
                pending_action=PendingAction.LOBBY_COMMAND,
            ),
            navigation_state=replace(
                state.navigation_state,
                lobby_submenu=screen.kind,
                selected_seat_index=screen.seat_index,
            ),
        )
    pending_action = PendingAction.NONE
    if screen.kind == "choose_card":
        pending_action = PendingAction.CHOOSE_CARD
    elif screen.kind == "choose_row":
        pending_action = PendingAction.CHOOSE_ROW
    client_mode = ClientMode.ENDED if screen.kind == "ended" else ClientMode.GAME
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=client_mode,
            pending_action=pending_action,
            player_state=screen.player_state,
        ),
    )


def _screen_from_state(state: CliState) -> Screen:
    core = state.core_state
    nav = state.navigation_state
    if core.client_mode == ClientMode.LOBBY:
        return LobbyScreen(kind=nav.lobby_submenu, seat_index=nav.selected_seat_index)
    if core.client_mode == ClientMode.ENDED:
        return GameScreen(kind="ended", player_state=core.player_state)
    if core.pending_action == PendingAction.CHOOSE_CARD:
        return GameScreen(kind="choose_card", player_state=core.player_state)
    if core.pending_action == PendingAction.CHOOSE_ROW:
        return GameScreen(kind="choose_row", player_state=core.player_state)
    return GameScreen(kind="waiting", player_state=core.player_state)
