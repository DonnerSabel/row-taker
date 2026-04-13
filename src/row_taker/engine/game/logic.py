from __future__ import annotations

import random
from collections.abc import Sequence

from .cards import Card, Deck
from .models import Player, PlayerID, Row, RowID
from .phases import Phase, PhaseInfo, StepAction
from .rules import place_card, take_row, target_row_index
from .state import (
    GameState,
    RevealedPlay,
    RowChoiceRequired,
    RulesConfig,
    TrickResolutionCursor,
    TrickResolutionStep,
    TrickResolutionSummary,
)


def make_deck() -> list[Card]:
    return Deck.create_standard_deck().cards


def setup_game(
    player_list: Sequence[str],
    *,
    rng: random.Random | None = None,
    config: RulesConfig | None = None,
    hand_size: int | None = None,
) -> GameState:
    if rng is None:
        rng = random.Random()

    RulesConfig.validate_player_count(len(player_list))

    if config is None:
        config = RulesConfig()

    if hand_size is not None and hand_size != config.hand_size:
        config = RulesConfig(
            hand_size=hand_size,
            row_count=config.row_count,
            row_capacity=config.row_capacity,
            end_score=config.end_score,
        )

    deck = make_deck()
    rng.shuffle(deck)

    players = [
        Player(
            player_id=PlayerID(f"player-{index}"),
            name=name,
        )
        for index, name in enumerate(player_list)
    ]
    rows = [Row(row_id=RowID(f"row-{index}")) for index in range(config.row_count)]

    state = GameState(
        config=config,
        players=players,
        rows=rows,
        deck=deck,
        round_no=1,
        trick_no=1,
        phase_info=PhaseInfo(
            phase=Phase.ROUND_SETUP,
            message="Preparing first round.",
        ),
    )
    _deal_new_round(state)
    return state


def _deal_new_round(state: GameState) -> None:
    for row in state.rows:
        row.cards.clear()

    for i in range(state.config.row_count):
        state.rows[i].cards.append(state.deck.pop())

    for player in state.players:
        player.hand.clear()
        for _ in range(state.config.hand_size):
            player.hand.append(state.deck.pop())
        player.hand.sort(key=lambda card: card.value)

    state.trick_no = 1
    state.selected_cards.clear()
    state.current_trick_revealed_plays = ()
    state.resolution_cursor = None
    state.phase_info = PhaseInfo(
        phase=Phase.CHOOSE_CARD,
        message="Choose one card.",
    )


def submit_play_card(state: GameState, player_id: PlayerID, card_value: int) -> None:
    if state.phase_info.phase != Phase.CHOOSE_CARD:
        raise ValueError(f"invalid phase for submit_play_card: {state.phase_info.phase!r}")

    state.validate_player_id(player_id)
    state.validate_no_selected_card_for_player(player_id)
    card = Card(card_value)
    state.validate_player_has_card(player_id, card)
    state.selected_cards[player_id] = card


def all_cards_selected(state: GameState) -> bool:
    expected_player_ids = {player.player_id for player in state.players}
    return set(state.selected_cards.keys()) == expected_player_ids


def begin_trick_resolution(state: GameState) -> tuple[RevealedPlay, ...]:
    state.validate_complete_play_selections()

    state.phase_info = PhaseInfo(
        phase=Phase.REVEAL_AND_RESOLVE,
        message="Revealing cards and resolving trick.",
    )

    for player_id, card in state.selected_cards.items():
        player = state.get_player_by_id(player_id)
        hand_index = next(
            index for index, hand_card in enumerate(player.hand) if hand_card.value == card.value
        )
        player.hand.pop(hand_index)

    ordered = sorted(state.selected_cards.items(), key=lambda item: item[1].value)
    state.current_trick_revealed_plays = tuple(
        RevealedPlay(player_id=player_id, card=card)
        for player_id, card in ordered
    )
    state.resolution_cursor = TrickResolutionCursor(
        remaining_player_ids=[player_id for player_id, _card in ordered],
    )
    return state.current_trick_revealed_plays


def current_revealed_plays(state: GameState) -> tuple[RevealedPlay, ...]:
    return state.current_trick_revealed_plays


def has_pending_row_choice(state: GameState) -> bool:
    return state.phase_info.phase == Phase.CHOOSE_ROW


def has_pending_resolution_step(state: GameState) -> bool:
    cursor = state.resolution_cursor
    return cursor is not None and bool(cursor.remaining_player_ids) and state.phase_info.phase != Phase.CHOOSE_ROW


def _append_current_trick_step(state: GameState, step: TrickResolutionStep) -> TrickResolutionStep:
    cursor = state.resolution_cursor
    if cursor is None:
        raise ValueError("missing resolution_cursor")
    cursor.steps.append(step)
    return step


def resolve_next_trick_step(state: GameState) -> TrickResolutionStep | RowChoiceRequired | None:
    cursor = state.resolution_cursor
    if cursor is None or not cursor.remaining_player_ids:
        return None
    if state.phase_info.phase == Phase.CHOOSE_ROW:
        return None

    player_id = cursor.remaining_player_ids.pop(0)
    card = state.selected_cards[player_id]
    row_index = target_row_index(state.rows, card)

    if row_index is None:
        selectable_row_ids = tuple(row.row_id for row in state.rows)
        state.phase_info = PhaseInfo(
            phase=Phase.CHOOSE_ROW,
            active_player_id=player_id,
            pending_card=card,
            selectable_row_ids=selectable_row_ids,
            message="Choose a row to take.",
        )
        return RowChoiceRequired(
            player_id=player_id,
            card=card,
            selectable_row_ids=selectable_row_ids,
        )

    target_row = state.rows[row_index]
    previous_cards = tuple(target_row.cards)
    bullheads, taken = place_card(
        state.rows,
        row_index,
        card,
        row_capacity=state.config.row_capacity,
    )
    action = StepAction.PLACED if taken is None else StepAction.TOOK_ROW_OVERFLOW
    if taken is not None:
        state.get_player_by_id(player_id).score += bullheads

    state.phase_info = PhaseInfo(
        phase=Phase.REVEAL_AND_RESOLVE,
        message="Revealing cards and resolving trick.",
    )

    return _append_current_trick_step(
        state,
        TrickResolutionStep(
            action=action,
            player_id=player_id,
            affected_row_id=target_row.row_id,
            played_card=card,
            taken_cards=tuple(previous_cards) if taken is not None else (),
            points_gained=bullheads if taken is not None else 0,
            new_row_cards=tuple(target_row.cards),
        ),
    )


def submit_choose_row(state: GameState, player_id: PlayerID, row_id: RowID) -> TrickResolutionStep:
    if state.phase_info.phase != Phase.CHOOSE_ROW:
        raise ValueError(f"invalid phase for submit_choose_row: {state.phase_info.phase!r}")

    expected_player_id = state.phase_info.active_player_id
    pending_card = state.phase_info.pending_card
    if expected_player_id is None or pending_card is None:
        raise ValueError("missing pending choose-row context")
    if player_id != expected_player_id:
        raise ValueError(
            f"choose-row player_id mismatch: expected {expected_player_id!r}, got {player_id!r}"
        )

    selectable_row_ids = tuple(state.phase_info.selectable_row_ids)
    if selectable_row_ids and row_id not in selectable_row_ids:
        raise ValueError(f"row_id {row_id!r} is not selectable in the current state")

    chosen_index = state.get_row_index(row_id)
    previous_cards = tuple(state.rows[chosen_index].cards)
    bullheads, _taken = take_row(state.rows, chosen_index)
    state.get_player_by_id(player_id).score += bullheads
    state.rows[chosen_index].cards = [pending_card]

    state.phase_info = PhaseInfo(
        phase=Phase.REVEAL_AND_RESOLVE,
        message="Revealing cards and resolving trick.",
    )

    return _append_current_trick_step(
        state,
        TrickResolutionStep(
            action=StepAction.TOOK_ROW_SMALL,
            player_id=player_id,
            affected_row_id=row_id,
            played_card=pending_card,
            taken_cards=tuple(previous_cards),
            points_gained=bullheads,
            new_row_cards=tuple(state.rows[chosen_index].cards),
        ),
    )


def trick_resolution_finished(state: GameState) -> bool:
    cursor = state.resolution_cursor
    return cursor is not None and not cursor.remaining_player_ids and state.phase_info.phase != Phase.CHOOSE_ROW


def finish_trick(state: GameState) -> TrickResolutionSummary:
    cursor = state.resolution_cursor
    if cursor is None:
        raise ValueError("missing resolution_cursor")
    steps = tuple(cursor.steps)

    state.phase_info = PhaseInfo(
        phase=Phase.ROUND_SCORING,
        message="Trick finished.",
    )
    state.selected_cards.clear()
    state.current_trick_revealed_plays = ()
    state.resolution_cursor = None

    new_round_started = start_next_round_if_needed(state)
    return TrickResolutionSummary(
        steps=steps,
        new_round_started=new_round_started,
        game_finished=state.phase_info.phase == Phase.GAME_OVER,
    )


def start_next_round_if_needed(state: GameState) -> bool:
    if any(player.hand for player in state.players):
        state.trick_no += 1
        state.phase_info = PhaseInfo(
            phase=Phase.CHOOSE_CARD,
            message="Choose one card.",
        )
        return False

    if any(player.score >= state.config.end_score for player in state.players):
        state.phase_info = PhaseInfo(
            phase=Phase.GAME_OVER,
            message="Game over.",
        )
        return False

    state.round_no += 1
    _deal_new_round(state)
    return True
