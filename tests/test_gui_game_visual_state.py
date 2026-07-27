from __future__ import annotations

from dataclasses import replace

from row_taker.client.core_state import PendingAction
from row_taker.client.state import UiMessage
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PublicState
from row_taker.gui.game_visual_builder import build_game_visual_state
from row_taker.gui_workbench.scenarios import get_scenario


def _state_with_rows(rows: tuple[Row, ...]):
    state = get_scenario("choose-card").state
    assert state.public_state is not None
    assert state.player_state is not None
    public_state = replace(state.public_state, rows=rows)
    player_state = replace(state.player_state, public_state=public_state)
    return replace(
        state,
        core_state=replace(
            state.core_state,
            public_state=public_state,
            player_state=player_state,
        ),
    )


def test_builder_sorts_rows_visually_and_preserves_row_ids() -> None:
    rows = (
        Row(RowID("high"), (Card(70), Card(90))),
        Row(RowID("low"), (Card(2), Card(12))),
        Row(RowID("middle"), (Card(20), Card(44))),
        Row(RowID("middle-b"), (Card(30), Card(44))),
    )
    visual_state = build_game_visual_state(
        _state_with_rows(rows),
        last_action_summary="test",
    )

    assert [row.row_id for row in visual_state.rows] == [
        RowID("low"),
        RowID("middle"),
        RowID("middle-b"),
        RowID("high"),
    ]
    assert {row.row_id for row in visual_state.rows} == {row.row_id for row in rows}
    assert visual_state.rows[0].card_values == (2, 12)


def test_builder_copies_players_hand_scores_and_revealed_cards() -> None:
    state = get_scenario("cards-revealed").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.own_player is not None
    assert visual_state.own_player.player_id == state.own_player_id
    assert visual_state.own_player.score == 12
    assert tuple(card.card_value for card in visual_state.hand) == (
        7,
        17,
        28,
        39,
        44,
        53,
        62,
        71,
        86,
        101,
    )
    assert {
        player.player_id: player.staged_card_value
        for player in visual_state.players
    } == {
        play.player_id: play.card_value
        for play in state.revealed_trick.plays
    }


def test_choose_card_interaction_contains_only_visible_hand_cards() -> None:
    state = get_scenario("choose-card").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.interaction.selectable_card_values == frozenset(
        card.card_value for card in visual_state.visible_hand
    )
    assert visual_state.interaction.selectable_row_ids == frozenset()
    assert visual_state.interaction.can_advance_presentation is False


def test_choose_row_interaction_and_prompt_come_from_client_semantics() -> None:
    state = get_scenario("choose-row").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.interaction.selectable_card_values == frozenset()
    assert visual_state.interaction.selectable_row_ids == frozenset(
        row.row_id for row in state.public_state.rows
    )
    assert visual_state.status.hand_prompt == "Reihe für Karte 7 wählen"


def test_presentation_interaction_suppresses_game_choices() -> None:
    state = get_scenario("cards-revealed").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert state.pending_action == PendingAction.CHOOSE_CARD
    assert visual_state.interaction.selectable_card_values == frozenset()
    assert visual_state.interaction.selectable_row_ids == frozenset()
    assert visual_state.interaction.can_advance_presentation is True


def test_status_text_and_message_level_are_built_before_rendering() -> None:
    state = get_scenario("choose-card").state
    state = replace(
        state,
        feedback_state=replace(
            state.feedback_state,
            flash_message=UiMessage(level="error", text="Ungültige Karte"),
        ),
    )
    visual_state = build_game_visual_state(
        state,
        last_action_summary="wird durch Flash ersetzt",
    )

    assert "Ada" in visual_state.status.primary_line
    assert f"Phase: {Phase.CHOOSE_CARD.value}" in visual_state.status.primary_line
    assert "Aktion: choose_card" in visual_state.status.primary_line
    assert visual_state.status.secondary_line == "Ungültige Karte"
    assert visual_state.status.message_level == "error"


def test_public_state_override_changes_visual_rows_without_changing_hand() -> None:
    state = get_scenario("choose-card").state
    assert state.public_state is not None
    override = PublicState(
        config=state.public_state.config,
        players=state.public_state.players,
        rows=(Row(RowID("override"), (Card(99),)),),
        round_no=state.public_state.round_no,
        trick_no=state.public_state.trick_no,
        phase_info=PhaseInfo(phase=Phase.REVEAL_AND_RESOLVE),
    )

    visual_state = build_game_visual_state(
        state,
        last_action_summary="test",
        public_state_override=override,
    )

    assert tuple(row.row_id for row in visual_state.rows) == (RowID("override"),)
    assert visual_state.status.primary_line.find("reveal_and_resolve") >= 0
    assert len(visual_state.hand) == len(state.player_state.hand)


def test_cards_revealed_panel_and_own_card_selection_live_in_visual_state() -> None:
    state = get_scenario("cards-revealed").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.presentation_panel is not None
    assert visual_state.presentation_panel.headline == "Karten aufgedeckt"
    assert visual_state.presentation_panel.card_values == (44, 62, 71, 86)
    assert len(visual_state.presentation_panel.details) == 3

    selected = tuple(
        card.card_value
        for card in visual_state.hand
        if card.emphasis == "selected"
    )
    assert selected == (44,)


def test_revealed_trick_fallback_stages_cards_without_opening_panel() -> None:
    state = get_scenario("card-placed").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.presentation_panel is None
    assert {
        player.player_id: player.staged_card_value
        for player in visual_state.players
    } == {
        play.player_id: play.card_value
        for play in state.revealed_trick.plays
    }
    assert all(card.emphasis == "none" for card in visual_state.hand)

