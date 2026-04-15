from __future__ import annotations

import random
from dataclasses import replace

from row_taker.client.core_state import ClientMode, PendingAction
from row_taker.client.presentation_events import (
    PresentationCardsRevealed,
    PresentationOverflowResolved,
    PresentationRowChoiceRequired,
)
from row_taker.client.state import (
    ClientState,
    UiMessage,
    enter_lobby_submenu,
    initial_client_state,
    with_core_updates,
    with_feedback_updates,
)
from row_taker.engine.game import Card, Phase, PhaseInfo, build_player_state, setup_game
from row_taker.protocol.messages import (
    LobbyParticipantView,
    LobbySeatView,
    LobbyView,
    PlayedCardView,
)


def build_demo_states() -> dict[str, ClientState]:
    return {
        "lobby": _build_lobby_state(),
        "choose_card": _build_choose_card_state(),
        "choose_row": _build_choose_row_state(),
        "presentation": _build_presentation_state(),
    }


def _build_lobby_state() -> ClientState:
    state = enter_lobby_submenu(
        initial_client_state("client-alice"),
        "seat_edit",
        selected_seat_index=1,
    )
    state = with_core_updates(
        state,
        own_player_id=None,
        lobby_view=LobbyView(
            seat_count=4,
            participants=(
                LobbyParticipantView(
                    client_id="client-alice",
                    display_name="Alice",
                    participant_kind="human",
                    seat_index=0,
                    endpoint="127.0.0.1:51001",
                ),
                LobbyParticipantView(
                    client_id="client-bot-1",
                    display_name="Bot Bruno",
                    participant_kind="bot",
                    seat_index=1,
                    endpoint="local",
                ),
                LobbyParticipantView(
                    client_id="client-carla",
                    display_name="Carla",
                    participant_kind="human",
                    seat_index=None,
                    endpoint="127.0.0.1:51002",
                ),
            ),
            seats=(
                LobbySeatView(0, "client-alice", "Alice", "human", "127.0.0.1:51001"),
                LobbySeatView(1, "client-bot-1", "Bot Bruno", "bot", "local"),
                LobbySeatView(2, None, None, None, None),
                LobbySeatView(3, None, None, None, None),
            ),
            game_started=False,
            server_endpoint="127.0.0.1:5000",
        ),
    )
    return with_feedback_updates(
        state,
        flash_message=UiMessage("info", "Seat 2 selected. Keys 1..4 switch demo scenes."),
    )


def _base_game_state() -> ClientState:
    game = setup_game(["Alice", "Bot Bruno", "Carla"], rng=random.Random(7))
    game.players[0].score = 7
    game.players[1].score = 11
    game.players[2].score = 0
    player_id = game.players[0].player_id
    player_state = build_player_state(game, player_id)
    return with_core_updates(
        initial_client_state("client-alice"),
        own_player_id=player_id,
        public_state=player_state.public_state,
        player_state=player_state,
        client_mode=ClientMode.GAME,
        pending_action=PendingAction.CHOOSE_CARD,
    )


def _build_choose_card_state() -> ClientState:
    state = _base_game_state()
    return with_feedback_updates(
        state,
        flash_message=UiMessage("info", "Choose one card. The hand panel is rendered from PlayerState."),
    )


def _build_choose_row_state() -> ClientState:
    state = _base_game_state()
    if state.player_state is None:
        return state

    public_state = replace(
        state.player_state.public_state,
        phase_info=PhaseInfo(
            phase=Phase.CHOOSE_ROW,
            active_player_id=state.player_state.self_player_id,
            pending_card=Card(3),
            selectable_row_ids=tuple(row.row_id for row in state.player_state.rows),
            message="Choose a row to take.",
        ),
    )
    player_state = replace(state.player_state, public_state=public_state)
    state = with_core_updates(
        state,
        public_state=public_state,
        player_state=player_state,
        pending_action=PendingAction.CHOOSE_ROW,
    )
    return with_feedback_updates(
        state,
        flash_message=UiMessage("info", "Choose-row phase: all rows are highlighted as selectable."),
    )


def _build_presentation_state() -> ClientState:
    state = _base_game_state()
    if state.player_state is None:
        return state

    presentation_events = (
        PresentationCardsRevealed(
            plays=(
                PlayedCardView(state.player_state.players[1].player_id, "Bot Bruno", 12),
                PlayedCardView(state.player_state.players[0].player_id, "Alice", 18),
                PlayedCardView(state.player_state.players[2].player_id, "Carla", 27),
            )
        ),
        PresentationRowChoiceRequired(
            player_id=state.player_state.players[1].player_id,
            player_name="Bot Bruno",
            card_value=12,
        ),
        PresentationOverflowResolved(
            player_id=state.player_state.players[0].player_id,
            player_name="Alice",
            row_id=state.player_state.rows[2].row_id,
            card_value=18,
            taken_cards=(44, 55, 66, 77, 88),
            bullheads=12,
            row_cards_after=(18,),
        ),
    )
    state = with_core_updates(
        state,
        pending_presentation_events=presentation_events,
        presentation_events=presentation_events[:1],
    )
    return with_feedback_updates(
        state,
        flash_message=UiMessage("info", "Presentation panel shows the semantic events, not just raw deltas."),
    )
