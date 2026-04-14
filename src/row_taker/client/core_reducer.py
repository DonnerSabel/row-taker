from __future__ import annotations

from dataclasses import dataclass, replace

from row_taker.cli.local_resolution import apply_local_row_choice, start_local_resolution
from row_taker.cli.row_display import build_row_display_mapping
from row_taker.cli.state_models import CliState, GameScreen, LobbyScreen, UiMessage, has_pending_presentation
from row_taker.client.actions import (
    UiAction,
    UiActionAdvancePresentation,
    UiActionAssignSelfToSeat,
    UiActionChooseCard,
    UiActionChooseRow,
    UiActionClearSeat,
    UiActionCreateBot,
    UiActionLeaveSession,
    UiActionRename,
    UiActionStartGame,
)
from row_taker.client.presentation_events import PresentationEvent
from row_taker.engine.game.player_state_ops import validate_submit_card, validate_submit_row_choice
from row_taker.protocol.messages import (
    AssignSeatToClient,
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    ClearSeat,
    ClientToServerMessage,
    CreateLocalBotOnSeat,
    GameStarting,
    IdentityAssigned,
    LeaveSession,
    LobbyActionRejected,
    LobbyStateUpdated,
    RequestStartGame,
    RowChoiceCommitted,
    ServerError,
    ServerToClientMessage,
    SessionEnded,
    SetDisplayName,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
)


@dataclass(frozen=True, slots=True)
class ActionResult:
    state: CliState
    outbound_message: ClientToServerMessage | None = None
    local_message: str | None = None


def append_presentation_events(state: CliState, events: tuple[PresentationEvent, ...]) -> CliState:
    if not events:
        return state
    return replace(state, pending_presentation_events=state.pending_presentation_events + events)


def advance_presentation_queue(state: CliState) -> CliState:
    if not state.pending_presentation_events:
        return state
    next_event = state.pending_presentation_events[0]
    return replace(
        state,
        presentation_events=state.presentation_events + (next_event,),
        pending_presentation_events=state.pending_presentation_events[1:],
    )


def reduce_server_message(state: CliState, message: ServerToClientMessage) -> CliState:
    match message:
        case IdentityAssigned(client_id=client_id):
            return replace(state, own_client_id=client_id)
        case LobbyStateUpdated(lobby=lobby):
            return replace(state, lobby_view=lobby)
        case LobbyActionRejected(message=text):
            return replace(state, flash_message=UiMessage(level="error", text=text))
        case GameStarting(lobby=lobby):
            return replace(
                state,
                lobby_view=lobby,
                public_state=None,
                screen=GameScreen(kind="waiting"),
                flash_message=UiMessage(level="info", text="Spielstart..."),
                revealed_trick=None,
                local_resolution=None,
                presentation_events=(),
                pending_presentation_events=(),
            )
        case StateUpdated(state=public_state):
            next_screen = state.screen
            if isinstance(next_screen, GameScreen) and next_screen.kind == "choose_row":
                next_screen = GameScreen(kind="waiting")
            next_local_resolution = state.local_resolution
            if next_local_resolution is not None and next_local_resolution.pending_row_choice is None:
                next_local_resolution = None
            return replace(
                state,
                public_state=public_state,
                screen=next_screen,
                revealed_trick=None,
                local_resolution=next_local_resolution,
            )
        case CardsRevealed() as revealed:
            local_resolution = None
            queued_events: tuple[PresentationEvent, ...] = ()
            if state.public_state is not None:
                local_resolution = start_local_resolution(state.public_state, revealed)
                queued_events = local_resolution.events
            next_state = replace(state, revealed_trick=revealed, local_resolution=local_resolution, flash_message=None)
            return append_presentation_events(next_state, queued_events)
        case RowChoiceCommitted(row_id=row_id):
            local_resolution = state.local_resolution
            newly_queued_events: tuple[PresentationEvent, ...] = ()
            if local_resolution is not None and local_resolution.pending_row_choice is not None:
                previous_count = len(local_resolution.events)
                local_resolution = apply_local_row_choice(local_resolution, row_id)
                newly_queued_events = local_resolution.events[previous_count:]
            next_state = replace(state, screen=GameScreen(kind="waiting"), local_resolution=local_resolution, flash_message=None)
            return append_presentation_events(next_state, newly_queued_events)
        case ChooseCardRequested(player_id=player_id, state=player_state):
            return replace(
                state,
                own_player_id=player_id,
                screen=GameScreen(kind="choose_card", player_state=player_state),
                flash_message=None,
                revealed_trick=None,
                local_resolution=None,
                presentation_events=(),
                pending_presentation_events=(),
            )
        case ChooseRowRequested(player_id=player_id, state=player_state):
            return replace(
                state,
                own_player_id=player_id,
                screen=GameScreen(kind="choose_row", player_state=player_state),
                flash_message=None,
            )
        case SessionEnded(message=text):
            return replace(
                state,
                session_error=text,
                exit_on_ack=False,
                suppress_final_result=True,
                should_exit=True,
                flash_message=None,
            )
        case ServerError(message=text):
            return replace(
                state,
                session_error=text,
                exit_on_ack=True,
                suppress_final_result=True,
                flash_message=None,
            )
        case _:
            raise TypeError(f"unsupported server message type: {type(message)!r}")


def apply_ui_action(state: CliState, action: UiAction) -> ActionResult:
    match action:
        case UiActionLeaveSession():
            return ActionResult(
                state=replace(state, should_exit=True, suppress_final_result=True),
                outbound_message=LeaveSession(),
            )
        case UiActionAdvancePresentation():
            return ActionResult(state=advance_presentation_queue(state))
        case UiActionRename(name=name):
            return ActionResult(
                state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
                outbound_message=SetDisplayName(display_name=name),
            )
        case UiActionAssignSelfToSeat(seat_index=seat_index):
            if state.own_client_id is None:
                return ActionResult(state=state, local_message="Eigene client_id unbekannt.")
            return ActionResult(
                state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
                outbound_message=AssignSeatToClient(seat_index=seat_index, target_client_id=state.own_client_id),
            )
        case UiActionCreateBot(seat_index=seat_index, name=name):
            return ActionResult(
                state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
                outbound_message=CreateLocalBotOnSeat(seat_index=seat_index, display_name=name),
            )
        case UiActionClearSeat(seat_index=seat_index):
            return ActionResult(
                state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
                outbound_message=ClearSeat(seat_index=seat_index),
            )
        case UiActionStartGame():
            return ActionResult(
                state=replace(state, screen=LobbyScreen(kind="main"), flash_message=None),
                outbound_message=RequestStartGame(),
            )
        case UiActionChooseCard(card_value=value):
            screen = state.screen
            player_state = screen.player_state if isinstance(screen, GameScreen) and screen.kind == "choose_card" else None
            if player_state is None:
                return ActionResult(state=state, local_message="Keine Kartenauswahl aktiv.")
            try:
                validate_submit_card(player_state, value)
            except Exception as exc:
                return ActionResult(state=state, local_message=str(exc))
            return ActionResult(
                state=replace(state, screen=GameScreen(kind="waiting"), flash_message=None),
                outbound_message=SubmitCard(card_value=value),
            )
        case UiActionChooseRow(row_id=row_id):
            screen = state.screen
            player_state = screen.player_state if isinstance(screen, GameScreen) and screen.kind == "choose_row" else None
            if player_state is None:
                return ActionResult(state=state, local_message="Keine Reihenwahl aktiv.")
            try:
                validate_submit_row_choice(player_state, row_id)
            except Exception as exc:
                return ActionResult(state=state, local_message=str(exc))
            return ActionResult(
                state=replace(state, screen=GameScreen(kind="waiting"), flash_message=None),
                outbound_message=SubmitRowChoice(row_id=row_id),
            )
        case _:
            raise TypeError(f"unsupported ui action type: {type(action)!r}")
