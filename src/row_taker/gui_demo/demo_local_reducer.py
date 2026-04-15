from __future__ import annotations

from dataclasses import replace

from row_taker.client.actions import (
    ClientActionAdvancePresentation,
    ClientActionAssignSelfToSeat,
    ClientActionChooseCard,
    ClientActionChooseRow,
    ClientActionClearSeat,
    ClientActionCreateBot,
    ClientActionStartGame,
)
from row_taker.client.core_state import ClientMode
from row_taker.client.state import (
    ClientState,
    UiMessage,
    enter_lobby_submenu,
    with_core_updates,
    with_feedback_updates,
    with_navigation_updates,
)
from row_taker.gui_demo.demo_state import build_demo_states
from row_taker.protocol.messages import LobbyParticipantView, LobbySeatView, LobbyView


def apply_demo_action(state: ClientState, action: object) -> tuple[ClientState, str | None]:
    if isinstance(action, ClientActionAssignSelfToSeat):
        return _assign_self_to_seat(state, action.seat_index), None
    if isinstance(action, ClientActionCreateBot):
        return _create_bot(state, action.seat_index, action.name), None
    if isinstance(action, ClientActionClearSeat):
        return _clear_seat(state, action.seat_index), None
    if isinstance(action, ClientActionStartGame):
        demo_states = build_demo_states()
        return demo_states["choose_card"], "choose_card"
    if isinstance(action, ClientActionChooseCard):
        return with_feedback_updates(
            state,
            flash_message=UiMessage("info", f"GUI produced ClientActionChooseCard(card_value={action.card_value})."),
        ), None
    if isinstance(action, ClientActionChooseRow):
        return with_feedback_updates(
            state,
            flash_message=UiMessage("info", f"GUI produced ClientActionChooseRow(row_id={action.row_id})."),
        ), None
    if isinstance(action, ClientActionAdvancePresentation):
        return _advance_presentation(state), None
    return state, None


def _assign_self_to_seat(state: ClientState, seat_index: int) -> ClientState:
    lobby_view = state.lobby_view
    own_client_id = state.own_client_id
    if lobby_view is None or own_client_id is None:
        return state

    own_participant = None
    other_participants: list[LobbyParticipantView] = []
    for participant in lobby_view.participants:
        if participant.client_id == own_client_id:
            own_participant = participant
        else:
            other_participants.append(participant)

    if own_participant is None:
        own_participant = LobbyParticipantView(
            client_id=own_client_id,
            display_name="Player",
            participant_kind="human",
            seat_index=seat_index,
            endpoint="local-demo",
        )
    else:
        own_participant = replace(own_participant, seat_index=seat_index)

    new_seats = tuple(_seat_with_self(seat, own_participant, seat_index) for seat in lobby_view.seats)
    new_participants = tuple([own_participant, *other_participants])
    new_lobby_view = replace(lobby_view, seats=new_seats, participants=new_participants)
    next_state = with_core_updates(state, lobby_view=new_lobby_view)
    next_state = enter_lobby_submenu(next_state, "main")
    return with_feedback_updates(next_state, flash_message=UiMessage("info", f"Demo: self assigned to seat {seat_index + 1}."))


def _create_bot(state: ClientState, seat_index: int, name: str) -> ClientState:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return state

    bot_client_id = f"demo-bot-{seat_index}"
    new_bot = LobbyParticipantView(
        client_id=bot_client_id,
        display_name=name,
        participant_kind="bot",
        seat_index=seat_index,
        endpoint="local-demo",
    )

    participants = [participant for participant in lobby_view.participants if participant.client_id != bot_client_id]
    participants.append(new_bot)
    new_seats = []
    for seat in lobby_view.seats:
        if seat.seat_index == seat_index:
            new_seats.append(
                LobbySeatView(
                    seat_index=seat.seat_index,
                    occupant_client_id=bot_client_id,
                    occupant_display_name=name,
                    occupant_kind="bot",
                    occupant_endpoint="local-demo",
                )
            )
        else:
            new_seats.append(seat)

    new_lobby_view = replace(lobby_view, seats=tuple(new_seats), participants=tuple(participants))
    next_state = with_core_updates(state, lobby_view=new_lobby_view)
    next_state = enter_lobby_submenu(next_state, "main")
    return with_feedback_updates(next_state, flash_message=UiMessage("info", f"Demo: bot '{name}' placed on seat {seat_index + 1}."))


def _clear_seat(state: ClientState, seat_index: int) -> ClientState:
    lobby_view = state.lobby_view
    if lobby_view is None:
        return state

    seat_to_clear = next((seat for seat in lobby_view.seats if seat.seat_index == seat_index), None)
    client_id_to_clear = seat_to_clear.occupant_client_id if seat_to_clear is not None else None

    new_seats = []
    for seat in lobby_view.seats:
        if seat.seat_index == seat_index:
            new_seats.append(
                LobbySeatView(
                    seat_index=seat.seat_index,
                    occupant_client_id=None,
                    occupant_display_name=None,
                    occupant_kind=None,
                    occupant_endpoint=None,
                )
            )
        else:
            new_seats.append(seat)

    new_participants = []
    for participant in lobby_view.participants:
        if participant.client_id == client_id_to_clear:
            if participant.client_id == state.own_client_id:
                new_participants.append(replace(participant, seat_index=None))
            continue
        new_participants.append(participant)

    if client_id_to_clear == state.own_client_id:
        new_participants = [
            replace(participant, seat_index=None) if participant.client_id == state.own_client_id else participant
            for participant in lobby_view.participants
        ]

    new_lobby_view = replace(lobby_view, seats=tuple(new_seats), participants=tuple(new_participants))
    next_state = with_core_updates(state, lobby_view=new_lobby_view)
    next_state = enter_lobby_submenu(next_state, "main")
    return with_feedback_updates(next_state, flash_message=UiMessage("info", f"Demo: cleared seat {seat_index + 1}."))


def _advance_presentation(state: ClientState) -> ClientState:
    if not state.pending_presentation_events:
        return with_feedback_updates(state, flash_message=UiMessage("info", "No pending presentation events."))

    visible = state.presentation_events + (state.pending_presentation_events[0],)
    pending = state.pending_presentation_events[1:]
    next_state = with_core_updates(
        state,
        presentation_events=visible,
        pending_presentation_events=pending,
    )
    if pending:
        return with_feedback_updates(next_state, flash_message=UiMessage("info", "Demo: advanced local presentation."))
    next_state = with_feedback_updates(next_state, flash_message=UiMessage("info", "Demo: presentation finished."))
    if state.client_mode == ClientMode.GAME:
        next_state = with_navigation_updates(next_state)
    return next_state


def _seat_with_self(seat: LobbySeatView, participant: LobbyParticipantView, seat_index: int) -> LobbySeatView:
    if seat.seat_index == seat_index:
        return LobbySeatView(
            seat_index=seat.seat_index,
            occupant_client_id=participant.client_id,
            occupant_display_name=participant.display_name,
            occupant_kind=participant.participant_kind,
            occupant_endpoint=participant.endpoint,
        )
    if seat.occupant_client_id == participant.client_id:
        return LobbySeatView(
            seat_index=seat.seat_index,
            occupant_client_id=None,
            occupant_display_name=None,
            occupant_kind=None,
            occupant_endpoint=None,
        )
    return seat
