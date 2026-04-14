from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from row_taker.client.core_state import ClientCoreState, ClientMode, PendingAction, initial_client_core_state
from row_taker.client.presentation_events import PresentationEvent
from row_taker.engine.game.state import PlayerState, PublicState
from row_taker.protocol.messages import CardsRevealed, LobbyView


@dataclass(frozen=True, slots=True)
class UiMessage:
    level: Literal["info", "error"]
    text: str


LobbySubmenu = Literal["main", "rename", "seat_edit", "bot_name"]


@dataclass(frozen=True, slots=True)
class ClientNavigationState:
    lobby_submenu: LobbySubmenu = "main"
    selected_seat_index: int | None = None


@dataclass(frozen=True, slots=True)
class ClientFeedbackState:
    flash_message: UiMessage | None = None
    exit_on_ack: bool = False
    suppress_final_result: bool = False
    should_exit: bool = False


@dataclass(frozen=True, slots=True)
class ClientState:
    core_state: ClientCoreState = field(default_factory=initial_client_core_state)
    navigation_state: ClientNavigationState = field(default_factory=ClientNavigationState)
    feedback_state: ClientFeedbackState = field(default_factory=ClientFeedbackState)

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
    def flash_message(self) -> UiMessage | None:
        return self.feedback_state.flash_message

    @property
    def revealed_trick(self) -> CardsRevealed | None:
        return self.core_state.revealed_trick

    @property
    def local_resolution(self):
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



def initial_client_state(own_client_id: str | None = None) -> ClientState:
    return ClientState(core_state=initial_client_core_state(own_client_id=own_client_id))



def has_pending_presentation(state: ClientState) -> bool:
    return bool(state.core_state.pending_presentation_events)



def has_visible_presentation(state: ClientState) -> bool:
    return bool(state.core_state.presentation_events)



def with_core_updates(state: ClientState, **changes: object) -> ClientState:
    return replace(state, core_state=replace(state.core_state, **changes))



def with_navigation_updates(state: ClientState, **changes: object) -> ClientState:
    return replace(state, navigation_state=replace(state.navigation_state, **changes))



def with_feedback_updates(state: ClientState, **changes: object) -> ClientState:
    return replace(state, feedback_state=replace(state.feedback_state, **changes))



def show_lobby_main(state: ClientState) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.LOBBY,
            pending_action=PendingAction.LOBBY_COMMAND,
        ),
        navigation_state=replace(
            state.navigation_state,
            lobby_submenu="main",
            selected_seat_index=None,
        ),
    )



def show_lobby_rename(state: ClientState) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.LOBBY,
            pending_action=PendingAction.LOBBY_COMMAND,
        ),
        navigation_state=replace(
            state.navigation_state,
            lobby_submenu="rename",
            selected_seat_index=None,
        ),
    )



def show_lobby_seat_edit(state: ClientState, seat_index: int) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.LOBBY,
            pending_action=PendingAction.LOBBY_COMMAND,
        ),
        navigation_state=replace(
            state.navigation_state,
            lobby_submenu="seat_edit",
            selected_seat_index=seat_index,
        ),
    )



def show_lobby_bot_name(state: ClientState, seat_index: int) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.LOBBY,
            pending_action=PendingAction.LOBBY_COMMAND,
        ),
        navigation_state=replace(
            state.navigation_state,
            lobby_submenu="bot_name",
            selected_seat_index=seat_index,
        ),
    )



def show_game_waiting(state: ClientState, player_state: PlayerState | None = None) -> ClientState:
    next_player_state = state.player_state if player_state is None else player_state
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.GAME,
            pending_action=PendingAction.NONE,
            player_state=next_player_state,
        ),
    )



def show_choose_card(state: ClientState, player_state: PlayerState) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.GAME,
            pending_action=PendingAction.CHOOSE_CARD,
            player_state=player_state,
        ),
    )



def show_choose_row(state: ClientState, player_state: PlayerState) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.GAME,
            pending_action=PendingAction.CHOOSE_ROW,
            player_state=player_state,
        ),
    )



def show_game_ended(state: ClientState, player_state: PlayerState | None = None) -> ClientState:
    next_player_state = state.player_state if player_state is None else player_state
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.ENDED,
            pending_action=PendingAction.NONE,
            player_state=next_player_state,
        ),
    )
