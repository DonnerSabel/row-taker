from __future__ import annotations

from row_taker.client.core_reducer import reduce_server_message
from row_taker.client.core_state import ClientCoreState, ClientMode, PendingAction
from row_taker.client.presentation_events import PresentationEvent
from row_taker.client.presentation_queue import advance_presentation_queue
from row_taker.client.state import ClientState, initial_client_state
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PlayerState, PublicState, RulesConfig
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import (
    CardsRevealed,
    ChooseRowRequested,
    IdentityAssigned,
    LobbyParticipantView,
    LobbySeatView,
    LobbyStateUpdated,
    LobbyView,
    PlayedCardView,
)


def build_lobby_view(
    occupants: tuple[tuple[str, str, ParticipantKind, str | None] | None, ...],
    *,
    extra_participants: tuple[tuple[str, str, ParticipantKind, str | None], ...] = (),
    endpoint: str = "127.0.0.1:8765",
) -> LobbyView:
    seats: list[LobbySeatView] = []
    participants: list[LobbyParticipantView] = []
    for seat_index, occupant in enumerate(occupants):
        if occupant is None:
            seats.append(
                LobbySeatView(
                    seat_index=seat_index,
                    occupant_client_id=None,
                    occupant_display_name=None,
                    occupant_kind=None,
                    occupant_endpoint=None,
                )
            )
            continue
        client_id, display_name, kind, occupant_endpoint = occupant
        seats.append(
            LobbySeatView(
                seat_index=seat_index,
                occupant_client_id=client_id,
                occupant_display_name=display_name,
                occupant_kind=kind,
                occupant_endpoint=occupant_endpoint,
            )
        )
        participants.append(
            LobbyParticipantView(
                client_id=client_id,
                display_name=display_name,
                participant_kind=kind,
                seat_index=seat_index,
                endpoint=occupant_endpoint,
            )
        )
    for client_id, display_name, kind, participant_endpoint in extra_participants:
        participants.append(
            LobbyParticipantView(
                client_id=client_id,
                display_name=display_name,
                participant_kind=kind,
                seat_index=None,
                endpoint=participant_endpoint,
            )
        )
    return LobbyView(
        seat_count=len(occupants),
        participants=tuple(participants),
        seats=tuple(seats),
        game_started=False,
        server_endpoint=endpoint,
    )
def build_lobby_state(
    lobby: LobbyView,
    *,
    own_client_id: str = "client-ada",
) -> ClientState:
    state = reduce_server_message(initial_client_state(), IdentityAssigned(own_client_id))
    return reduce_server_message(state, LobbyStateUpdated(lobby=lobby))
def build_game_state(
    *,
    phase: Phase = Phase.CHOOSE_CARD,
    pending_action: PendingAction = PendingAction.CHOOSE_CARD,
    pending_card: Card | None = None,
    selectable_row_ids: tuple[RowID, ...] = (),
    rows: tuple[Row, ...] | None = None,
    player_names: tuple[str, ...] = ("Ada", "Ben", "Clara", "Dorian"),
) -> ClientState:
    player_ids = tuple(PlayerID(f"player-{index}") for index in range(len(player_names)))
    own_player_id = player_ids[0]
    hand = tuple(Card(value) for value in (7, 17, 28, 39, 44, 53, 61, 70, 85, 101))

    if rows is None:
        rows = (
            Row(RowID("row-0"), (Card(12), Card(21))),
            Row(RowID("row-1"), (Card(25), Card(31), Card(36))),
            Row(RowID("row-2"), (Card(43), Card(52), Card(58))),
            Row(RowID("row-3"), (Card(64), Card(69), Card(75))),
        )

    phase_info = PhaseInfo(
        phase=phase,
        active_player_id=own_player_id if phase == Phase.CHOOSE_ROW else None,
        pending_card=pending_card,
        selectable_row_ids=selectable_row_ids,
        message="Choose a row to take." if phase == Phase.CHOOSE_ROW else "Choose one card.",
    )
    players = tuple(
        PublicPlayerInfo(
            player_id=player_id,
            name=name,
            score=(12, 7, 18, 4)[index] if index < 4 else index,
            hand_count=len(hand),
        )
        for index, (player_id, name) in enumerate(zip(player_ids, player_names, strict=True))
    )
    public_state = PublicState(
        config=RulesConfig(),
        players=players,
        rows=rows,
        round_no=2,
        trick_no=4,
        phase_info=phase_info,
    )
    player_state = PlayerState(
        public_state=public_state,
        self_player_id=own_player_id,
        hand=hand,
    )
    return ClientState(
        core_state=ClientCoreState(
            own_client_id="client-0",
            own_player_id=own_player_id,
            public_state=public_state,
            player_state=player_state,
            client_mode=ClientMode.GAME,
            pending_action=pending_action,
        )
    )
def build_revealed_state(
    plays: tuple[tuple[int, int], ...],
    *,
    rows: tuple[Row, ...] | None = None,
    player_names: tuple[str, ...] = ("Ada", "Ben", "Clara", "Dorian"),
) -> ClientState:
    state = build_game_state(rows=rows, player_names=player_names)
    assert state.public_state is not None
    revealed = CardsRevealed(
        plays=tuple(
            PlayedCardView(
                player_id=state.public_state.players[player_index].player_id,
                player_name=state.public_state.players[player_index].name,
                card_value=card_value,
            )
            for player_index, card_value in plays
        )
    )
    return reduce_server_message(state, revealed)
def with_choose_row_request(state: ClientState) -> ClientState:
    player_state = state.player_state
    public_state = state.public_state
    if player_state is None or public_state is None:
        raise ValueError("choose-row scenario requires a player state")

    selectable_row_ids = tuple(row.row_id for row in public_state.rows)
    phase_info = PhaseInfo(
        phase=Phase.CHOOSE_ROW,
        active_player_id=player_state.self_player_id,
        pending_card=Card(7),
        selectable_row_ids=selectable_row_ids,
        message="Choose a row to take.",
    )
    choose_row_public_state = PublicState(
        config=public_state.config,
        players=public_state.players,
        rows=public_state.rows,
        round_no=public_state.round_no,
        trick_no=public_state.trick_no,
        phase_info=phase_info,
    )
    choose_row_player_state = PlayerState(
        public_state=choose_row_public_state,
        self_player_id=player_state.self_player_id,
        hand=player_state.hand,
    )
    return reduce_server_message(
        state,
        ChooseRowRequested(
            player_id=player_state.self_player_id,
            state=choose_row_player_state,
        ),
    )
def advance_to_event(
    state: ClientState,
    event_type: type[PresentationEvent],
) -> ClientState:
    current = state
    while current.pending_presentation_steps:
        if isinstance(current.pending_presentation_steps[0].event, event_type):
            return current
        current = advance_presentation_queue(current)
    raise ValueError(f"scenario could not find pending event {event_type.__name__}")
