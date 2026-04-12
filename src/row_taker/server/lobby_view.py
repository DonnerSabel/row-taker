from __future__ import annotations

from collections.abc import Mapping

from row_taker.engine.lobby.state import LobbyState
from row_taker.protocol.messages import (
    LobbyParticipantView,
    LobbySeatView,
    LobbyStateUpdated,
    LobbyView,
)
from row_taker.server.client_registry import ClientRegistry


def build_lobby_view(
    lobby_state: LobbyState,
    registry: ClientRegistry,
    pending_bot_display_names: Mapping[int, str] | None = None,
) -> LobbyView:
    pending_bot_display_names = pending_bot_display_names or {}
    participant_seat_map = {
        seat.occupant_client_id: seat.seat_index
        for seat in lobby_state.seats
        if seat.occupant_client_id is not None
    }
    participants = [
        LobbyParticipantView(
            client_id=participant.client_id,
            display_name=participant.display_name,
            participant_kind=participant.kind.value,
            seat_index=participant_seat_map.get(participant.client_id),
            endpoint=participant.endpoint_display,
        )
        for participant in registry.list_participants()
    ]
    for seat_index, display_name in pending_bot_display_names.items():
        participants.append(
            LobbyParticipantView(
                client_id=f"pending-bot-seat-{seat_index}",
                display_name=display_name,
                participant_kind="bot",
                seat_index=seat_index,
                endpoint=None,
            )
        )
    seats = []
    for seat in lobby_state.seats:
        occupant_client_id = seat.occupant_client_id
        occupant_display_name = None
        occupant_kind = None
        occupant_endpoint = None
        if occupant_client_id is not None:
            participant = registry.get_participant(occupant_client_id)
            occupant_display_name = participant.display_name
            occupant_kind = participant.kind.value
            occupant_endpoint = participant.endpoint_display
        elif seat.seat_index in pending_bot_display_names:
            occupant_client_id = f"pending-bot-seat-{seat.seat_index}"
            occupant_display_name = pending_bot_display_names[seat.seat_index]
            occupant_kind = "bot"
        seats.append(
            LobbySeatView(
                seat_index=seat.seat_index,
                occupant_client_id=occupant_client_id,
                occupant_display_name=occupant_display_name,
                occupant_kind=occupant_kind,
                occupant_endpoint=occupant_endpoint,
            )
        )
    return LobbyView(
        seat_count=lobby_state.seat_count,
        participants=tuple(
            sorted(participants, key=lambda participant: participant.display_name.casefold())
        ),
        seats=tuple(seats),
        game_started=lobby_state.game_started,
    )


def build_lobby_state_updated(
    lobby_state: LobbyState,
    registry: ClientRegistry,
    pending_bot_display_names: Mapping[int, str] | None = None,
) -> LobbyStateUpdated:
    return LobbyStateUpdated(
        lobby=build_lobby_view(lobby_state, registry, pending_bot_display_names)
    )
