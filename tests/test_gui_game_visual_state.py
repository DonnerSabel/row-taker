from __future__ import annotations

from dataclasses import replace

from row_taker.client.core_reducer import advance_presentation_queue
from row_taker.client.core_state import PendingAction
from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
)
from row_taker.client.state import UiMessage
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PublicState
from row_taker.gui.game_visual_builder import build_game_visual_state
from row_taker.gui.game_visual_state import PlayerPlayAnchor, RowCardAnchor
from row_taker.gui.game_visual_static import build_stable_game_visual_state
from row_taker.gui_workbench.scenarios import get_scenario
from row_taker.gui_workbench.timeline import get_timeline


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
    assert {player.player_id: player.staged_card_value for player in visual_state.players} == {
        play.player_id: play.card_value for play in state.revealed_trick.plays
    }


def test_choose_card_interaction_contains_only_visible_hand_cards() -> None:
    state = get_scenario("choose-card").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.interaction.selectable_card_values == frozenset(
        card.card_value for card in visual_state.visible_hand
    )
    assert visual_state.interaction.selectable_row_ids == frozenset()
    assert visual_state.interaction.can_advance_presentation is False


def test_choose_row_interaction_and_action_line_come_from_client_semantics() -> None:
    state = get_scenario("choose-row").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.interaction.selectable_card_values == frozenset()
    assert visual_state.interaction.selectable_row_ids == frozenset(
        row.row_id for row in state.public_state.rows
    )
    assert visual_state.status.action_line == "Reihe für Karte 7 wählen"


def test_presentation_interaction_suppresses_game_choices() -> None:
    state = get_scenario("cards-revealed").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert state.pending_action == PendingAction.CHOOSE_CARD
    assert visual_state.interaction.selectable_card_values == frozenset()
    assert visual_state.interaction.selectable_row_ids == frozenset()
    assert visual_state.interaction.can_advance_presentation is True
    assert visual_state.status.action_line == "Klicken zum Fortfahren"


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

    assert visual_state.status.game_line == "Runde 2 · Stich 4"
    assert visual_state.status.action_line == "Karte auswählen"
    assert visual_state.status.message_line == "Ungültige Karte"
    assert visual_state.status.message_level == "error"


def test_stable_builder_uses_supplied_public_state_without_changing_hand() -> None:
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

    visual_state = build_stable_game_visual_state(
        state,
        public_state=override,
        last_action_summary="test",
    )

    assert tuple(row.row_id for row in visual_state.rows) == (RowID("override"),)
    assert visual_state.status.game_line == (
        f"Runde {override.round_no} · Stich {override.trick_no}"
    )
    assert visual_state.status.action_line == "Karte auswählen"
    assert len(visual_state.hand) == len(state.player_state.hand)


def test_cards_revealed_panel_and_own_card_staging_live_in_visual_state() -> None:
    state = get_scenario("cards-revealed").state
    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.presentation_panel is not None
    assert visual_state.presentation_panel.headline == "Karten aufgedeckt"
    assert len(visual_state.presentation_panel.details) == 3

    own_player = visual_state.own_player
    assert own_player is not None
    assert own_player.staged_card_value == 44
    own_hand_card = next(card for card in visual_state.hand if card.card_value == 44)
    assert own_hand_card.visible is False
    assert own_hand_card.emphasis == "none"


def test_card_placed_uses_before_and_after_snapshots_with_one_motion() -> None:
    state = get_scenario("card-placed").state
    step = state.current_presentation_step
    assert step is not None
    assert isinstance(step.event, PresentationCardPlaced)
    event = step.event

    before = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=0,
    )
    middle = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=16,
    )
    after = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=32,
    )

    before_row = before.row_by_id(event.row_id)
    after_row = after.row_by_id(event.row_id)
    assert before_row is not None
    assert after_row is not None
    assert before_row.card_values == tuple(
        card.value
        for card in step.public_state_before.rows[
            step.public_state_before.get_row_index(event.row_id)
        ].cards
    )
    assert after_row.card_values == event.row_cards_after
    assert before_row.emphasis == "placed"
    assert after_row.emphasis == "placed"

    assert len(before.moving_cards) == 1
    assert len(middle.moving_cards) == 1
    motion = middle.moving_cards[0]
    assert motion.card_value == event.card_value
    assert motion.source == PlayerPlayAnchor(event.player_id, event.card_value)
    assert motion.target == RowCardAnchor(event.row_id, len(event.row_cards_after) - 1)
    assert motion.progress == 0.875
    assert after.moving_cards == ()

    active_player = next(player for player in middle.players if player.player_id == event.player_id)
    assert active_player.emphasis == "active"
    assert active_player.staged_card_value is None
    if event.player_id == state.own_player_id:
        own_card = next(card for card in middle.hand if card.card_value == event.card_value)
        assert own_card.visible is False

    assert middle.presentation_panel is not None
    assert middle.presentation_panel.headline == f"{event.player_name} legt {event.card_value}"


def test_completed_card_placement_stays_hidden_in_following_step() -> None:
    state = get_scenario("card-placed").state
    first_step = state.current_presentation_step
    assert first_step is not None
    assert isinstance(first_step.event, PresentationCardPlaced)

    following = advance_presentation_queue(state)
    next_step = following.current_presentation_step
    assert next_step is not None
    assert isinstance(next_step.event, PresentationCardPlaced)

    visual_state = build_game_visual_state(
        following,
        last_action_summary="test",
        presentation_elapsed_frames=0,
    )
    completed_player = next(
        player for player in visual_state.players if player.player_id == first_step.event.player_id
    )
    assert completed_player.staged_card_value is None
    if first_step.event.player_id == following.own_player_id:
        completed_card = next(
            card for card in visual_state.hand if card.card_value == first_step.event.card_value
        )
        assert completed_card.visible is False


def test_card_placed_keeps_target_row_in_final_visual_column() -> None:
    state = get_scenario("card-placed").state
    current_step = state.current_presentation_step
    assert current_step is not None
    assert state.own_player_id is not None

    target_row_id = RowID("target")
    before_rows = (
        Row(RowID("low"), (Card(10),)),
        Row(target_row_id, (Card(20),)),
        Row(RowID("middle"), (Card(30),)),
        Row(RowID("high"), (Card(40),)),
    )
    after_rows = (
        before_rows[0],
        Row(target_row_id, (Card(20), Card(39))),
        before_rows[2],
        before_rows[3],
    )
    before_public = replace(current_step.public_state_before, rows=before_rows)
    after_public = replace(current_step.public_state_after, rows=after_rows)
    event = PresentationCardPlaced(
        player_id=state.own_player_id,
        player_name="Ada",
        card_value=39,
        row_id=target_row_id,
        row_cards_after=(20, 39),
    )
    custom_step = replace(
        current_step,
        event=event,
        public_state_before=before_public,
        public_state_after=after_public,
    )
    state = replace(
        state,
        core_state=replace(
            state.core_state,
            pending_presentation_steps=(custom_step,),
        ),
    )

    before = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=0,
    )
    after = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=32,
    )

    expected_order = (
        RowID("low"),
        RowID("middle"),
        target_row_id,
        RowID("high"),
    )
    assert tuple(row.row_id for row in before.rows) == expected_order
    assert tuple(row.row_id for row in after.rows) == expected_order
    assert before.moving_cards[0].target == RowCardAnchor(target_row_id, 1)


def test_row_choice_required_lives_in_visual_state() -> None:
    state = get_scenario("row-choice-required").state
    current_step = state.current_presentation_step
    assert current_step is not None
    assert isinstance(current_step.event, PresentationRowChoiceRequired)
    event = current_step.event

    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.presentation_panel is not None
    assert visual_state.presentation_panel.headline == f"{event.player_name} muss eine Reihe wählen"
    assert visual_state.interaction.can_advance_presentation is True
    assert all(row.emphasis == "none" for row in visual_state.rows)

    active_player = next(
        player for player in visual_state.players if player.player_id == event.player_id
    )
    assert active_player.emphasis == "active"
    assert active_player.staged_card_value == event.card_value

    if event.player_id == state.own_player_id:
        own_card = next(card for card in visual_state.hand if card.card_value == event.card_value)
        assert own_card.visible is False


def test_row_chosen_lives_in_visual_state_and_marks_stable_row_id() -> None:
    state = get_timeline("full-trick").steps[4].state
    current_step = state.current_presentation_step
    assert current_step is not None
    assert isinstance(current_step.event, PresentationRowChosen)
    event = current_step.event

    visual_state = build_game_visual_state(state, last_action_summary="test")

    assert visual_state.presentation_panel is not None
    assert (
        visual_state.presentation_panel.headline
        == f"{event.player_name} wählt Reihe {event.row_id}"
    )
    assert visual_state.interaction.can_advance_presentation is True

    chosen_row = visual_state.row_by_id(event.row_id)
    assert chosen_row is not None
    assert chosen_row.emphasis == "choice"
    assert sum(row.emphasis == "choice" for row in visual_state.rows) == 1

    active_player = next(
        player for player in visual_state.players if player.player_id == event.player_id
    )
    assert active_player.emphasis == "active"
    assert active_player.staged_card_value == event.card_value


def test_row_taken_uses_snapshot_scores_row_replacement_and_one_motion() -> None:
    state = get_scenario("row-taken").state
    step = state.current_presentation_step
    assert step is not None
    assert isinstance(step.event, PresentationRowTaken)
    event = step.event

    before = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=0,
    )
    middle = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=16,
    )
    after = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=32,
    )

    before_row = before.row_by_id(event.row_id)
    middle_row = middle.row_by_id(event.row_id)
    after_row = after.row_by_id(event.row_id)
    assert before_row is not None
    assert middle_row is not None
    assert after_row is not None
    assert before_row.card_values == event.taken_cards
    assert middle_row.card_values == event.taken_cards
    assert after_row.card_values == event.row_cards_after
    assert before_row.emphasis == "taken"
    assert middle_row.emphasis == "taken"
    assert after_row.emphasis == "taken"
    assert tuple(card.card_value for card in before_row.taken_cards) == event.taken_cards
    assert tuple(card.card_value for card in after_row.taken_cards) == event.taken_cards

    before_player = next(player for player in before.players if player.player_id == event.player_id)
    after_player = next(player for player in after.players if player.player_id == event.player_id)
    before_snapshot_player = next(
        player for player in step.public_state_before.players if player.player_id == event.player_id
    )
    after_snapshot_player = next(
        player for player in step.public_state_after.players if player.player_id == event.player_id
    )
    assert before_player.score == before_snapshot_player.score
    assert after_player.score == after_snapshot_player.score
    assert after_player.score == before_player.score + event.bullheads

    assert len(before.moving_cards) == 1
    assert len(middle.moving_cards) == 1
    motion = middle.moving_cards[0]
    assert motion.card_value == event.replacement_card_value
    assert motion.source == PlayerPlayAnchor(
        event.player_id,
        event.replacement_card_value,
    )
    assert motion.target == RowCardAnchor(event.row_id, 0)
    assert motion.progress == 0.875
    assert after.moving_cards == ()

    assert before_player.emphasis == "active"
    assert before_player.staged_card_value is None
    if event.player_id == state.own_player_id:
        own_card = next(
            card for card in middle.hand if card.card_value == event.replacement_card_value
        )
        assert own_card.visible is False

    assert middle.presentation_panel is not None
    assert middle.presentation_panel.headline == f"{event.player_name} nimmt Reihe {event.row_id}"


def test_row_taken_keeps_replaced_row_in_one_visual_column() -> None:
    state = get_scenario("row-taken").state
    step = state.current_presentation_step
    assert step is not None
    assert isinstance(step.event, PresentationRowTaken)

    before = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=0,
    )
    after = build_game_visual_state(
        state,
        last_action_summary="test",
        presentation_elapsed_frames=32,
    )

    assert tuple(row.row_id for row in before.rows) == tuple(row.row_id for row in after.rows)
    assert before.moving_cards[0].target == RowCardAnchor(step.event.row_id, 0)
