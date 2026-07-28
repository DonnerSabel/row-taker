from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal

from row_taker.client.core_state import (
    ClientCoreState,
    ClientMode,
    PendingAction,
    initial_client_core_state,
)
from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.trick_presentation_resolver import TrickPresentationState
from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.state import PlayerState, PublicState
from row_taker.protocol.messages import CardsRevealed, LobbyView

UiMessageLevel = Literal["info", "error"]


@dataclass(frozen=True, slots=True)
class UiMessage:
    level: UiMessageLevel
    text: str


LobbySubmenu = Literal["main", "rename", "seat_edit", "bot_name"]


@dataclass(frozen=True, slots=True)
class ClientNavigationState:
    lobby_submenu: LobbySubmenu = "main"
    selected_seat_index: int | None = None
    bot_name_text: str = ""
    bot_name_selected: bool = False


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
    def own_player_id(self) -> PlayerID | None:
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
    def trick_presentation_state(self) -> TrickPresentationState | None:
        return self.core_state.trick_presentation_state

    @property
    def presentation_steps(self) -> tuple[PresentationStep, ...]:
        return self.core_state.presentation_steps

    @property
    def pending_presentation_steps(self) -> tuple[PresentationStep, ...]:
        return self.core_state.pending_presentation_steps

    @property
    def current_presentation_step(self) -> PresentationStep | None:
        if not self.pending_presentation_steps:
            return None
        return self.pending_presentation_steps[0]

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
    return bool(state.core_state.pending_presentation_steps)


def has_visible_presentation(state: ClientState) -> bool:
    return bool(state.core_state.presentation_steps)


def assign_identity(state: ClientState, client_id: str) -> ClientState:
    return replace(state, core_state=replace(state.core_state, own_client_id=client_id))


def update_lobby_view(state: ClientState, lobby: LobbyView) -> ClientState:
    return replace(state, core_state=replace(state.core_state, lobby_view=lobby))


def prepare_game_start(state: ClientState, lobby: LobbyView) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            lobby_view=lobby,
            public_state=None,
            player_state=None,
            revealed_trick=None,
            trick_presentation_state=None,
            presentation_steps=(),
            pending_presentation_steps=(),
            client_mode=ClientMode.GAME,
            pending_action=PendingAction.NONE,
        ),
    )


def apply_public_state(
    state: ClientState,
    public_state: PublicState,
    *,
    trick_presentation_state: TrickPresentationState | None,
) -> ClientState:
    pending_action = state.pending_action
    client_mode = state.client_mode
    if pending_action == PendingAction.CHOOSE_ROW:
        pending_action = PendingAction.NONE
        client_mode = ClientMode.GAME
    return replace(
        state,
        core_state=replace(
            state.core_state,
            public_state=public_state,
            revealed_trick=None,
            trick_presentation_state=trick_presentation_state,
            client_mode=client_mode,
            pending_action=pending_action,
        ),
    )


def record_revealed_trick(
    state: ClientState,
    revealed: CardsRevealed,
    *,
    trick_presentation_state: TrickPresentationState | None,
) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            revealed_trick=revealed,
            trick_presentation_state=trick_presentation_state,
        ),
    )


def set_trick_presentation_state(
    state: ClientState,
    presentation_state: TrickPresentationState | None,
) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            trick_presentation_state=presentation_state,
        ),
    )


def append_pending_presentation_steps(
    state: ClientState,
    steps: tuple[PresentationStep, ...],
) -> ClientState:
    if not steps:
        return state
    return replace(
        state,
        core_state=replace(
            state.core_state,
            pending_presentation_steps=state.pending_presentation_steps + steps,
        ),
    )


def advance_presentation_queue(state: ClientState) -> ClientState:
    if not state.pending_presentation_steps:
        return state
    next_step = state.pending_presentation_steps[0]
    return replace(
        state,
        core_state=replace(
            state.core_state,
            presentation_steps=state.presentation_steps + (next_step,),
            pending_presentation_steps=state.pending_presentation_steps[1:],
        ),
    )


def request_card_choice(
    state: ClientState,
    player_id: PlayerID,
    player_state: PlayerState,
) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            own_player_id=player_id,
            public_state=player_state.public_state,
            player_state=player_state,
            revealed_trick=None,
            trick_presentation_state=None,
            presentation_steps=(),
            pending_presentation_steps=(),
            client_mode=ClientMode.GAME,
            pending_action=PendingAction.CHOOSE_CARD,
        ),
    )


def request_row_choice(
    state: ClientState,
    player_id: PlayerID,
    player_state: PlayerState,
) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            own_player_id=player_id,
            public_state=player_state.public_state,
            player_state=player_state,
            client_mode=ClientMode.GAME,
            pending_action=PendingAction.CHOOSE_ROW,
        ),
    )


def record_received_game_revision(state: ClientState, revision: int) -> ClientState:
    return replace(
        state,
        core_state=replace(state.core_state, received_game_revision=revision),
    )


def record_applied_game_revision(state: ClientState, revision: int) -> ClientState:
    return replace(
        state,
        core_state=replace(state.core_state, applied_game_revision=revision),
    )


def set_session_error(state: ClientState, message: str) -> ClientState:
    return replace(state, core_state=replace(state.core_state, session_error=message))


def set_flash_message(state: ClientState, message: UiMessage) -> ClientState:
    return replace(
        state,
        feedback_state=replace(state.feedback_state, flash_message=message),
    )


def clear_flash_message(state: ClientState) -> ClientState:
    return replace(
        state,
        feedback_state=replace(state.feedback_state, flash_message=None),
    )


def request_exit(
    state: ClientState,
    *,
    suppress_final_result: bool = False,
) -> ClientState:
    return replace(
        state,
        feedback_state=replace(
            state.feedback_state,
            should_exit=True,
            suppress_final_result=suppress_final_result,
        ),
    )


def set_exit_on_ack(state: ClientState, enabled: bool) -> ClientState:
    return replace(
        state,
        feedback_state=replace(state.feedback_state, exit_on_ack=enabled),
    )


def mark_session_ended(state: ClientState, message: str) -> ClientState:
    next_state = set_session_error(state, message)
    return replace(
        next_state,
        feedback_state=replace(
            next_state.feedback_state,
            flash_message=None,
            exit_on_ack=False,
            suppress_final_result=True,
            should_exit=True,
        ),
    )


def mark_server_error(state: ClientState, message: str) -> ClientState:
    next_state = set_session_error(state, message)
    return replace(
        next_state,
        feedback_state=replace(
            next_state.feedback_state,
            flash_message=None,
            exit_on_ack=True,
            suppress_final_result=True,
        ),
    )


def mark_transport_closed(state: ClientState, message: str) -> ClientState:
    next_state = set_session_error(state, message)
    return set_exit_on_ack(next_state, False)


def enter_lobby_submenu(
    state: ClientState,
    submenu: LobbySubmenu,
    *,
    selected_seat_index: int | None = None,
) -> ClientState:
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.LOBBY,
            pending_action=PendingAction.LOBBY_COMMAND,
        ),
        navigation_state=replace(
            state.navigation_state,
            lobby_submenu=submenu,
            selected_seat_index=selected_seat_index,
        ),
    )


def set_bot_name_editor(
    state: ClientState,
    *,
    text: str,
    selected: bool,
) -> ClientState:
    return replace(
        state,
        navigation_state=replace(
            state.navigation_state,
            bot_name_text=text,
            bot_name_selected=selected,
        ),
    )


def select_bot_name_text(state: ClientState) -> ClientState:
    return replace(
        state,
        navigation_state=replace(state.navigation_state, bot_name_selected=True),
    )


def clear_bot_name_editor(state: ClientState) -> ClientState:
    return set_bot_name_editor(state, text="", selected=False)


def enter_game_mode(
    state: ClientState,
    *,
    pending_action: PendingAction,
    player_state: PlayerState | None = None,
) -> ClientState:
    next_player_state = state.player_state if player_state is None else player_state
    return replace(
        state,
        core_state=replace(
            state.core_state,
            client_mode=ClientMode.GAME,
            pending_action=pending_action,
            player_state=next_player_state,
        ),
    )


def enter_ended_mode(state: ClientState, player_state: PlayerState | None = None) -> ClientState:
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
