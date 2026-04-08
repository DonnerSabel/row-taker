from __future__ import annotations

from row_taker.engine.lobby.state import LobbyState
from row_taker.protocol.messages import LobbyParticipantView, LobbySeatView, LobbyView, LobbyStateUpdated
from row_taker.server.client_registry import ClientRegistry


def build_lobby_view(lobby_state: LobbyState, registry: ClientRegistry) -> LobbyView:
    participant_seat_map = {
        seat.occupant_client_id: seat.seat_index
        for seat in lobby_state.seats
        if seat.occupant_client_id is not None
    }
    participants = tuple(
        LobbyParticipantView(
            client_id=participant.client_id,
            display_name=participant.display_name,
            participant_kind=participant.kind.value,
            seat_index=participant_seat_map.get(participant.client_id),
        )
        for participant in sorted(registry.list_participants(), key=lambda participant: participant.display_name.casefold())
    )
    seats = []
    for seat in lobby_state.seats:
        occupant_client_id = seat.occupant_client_id
        occupant_display_name = None
        occupant_kind = None
        if occupant_client_id is not None:
            participant = registry.get_participant(occupant_client_id)
            occupant_display_name = participant.display_name
            occupant_kind = participant.kind.value
        seats.append(
            LobbySeatView(
                seat_index=seat.seat_index,
                occupant_client_id=occupant_client_id,
                occupant_display_name=occupant_display_name,
                occupant_kind=occupant_kind,
            )
        )
    return LobbyView(
        seat_count=lobby_state.seat_count,
        participants=participants,
        seats=tuple(seats),
        game_started=lobby_state.game_started,
    )


def build_lobby_state_updated(lobby_state: LobbyState, registry: ClientRegistry) -> LobbyStateUpdated:
    return LobbyStateUpdated(lobby=build_lobby_view(lobby_state, registry))
