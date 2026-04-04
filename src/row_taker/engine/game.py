from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .commands import ChooseRowCommand, PlayCardCommand
from .models import Card, Player, PlayerID, Row, RowID
from .phases import Phase, PhaseInfo
from .rules import place_card, take_row, target_row_index
from .state import GameState, RulesConfig


ChooseRowFn = Callable[[GameState, PlayerID, Card], RowID | ChooseRowCommand]


def make_deck() -> list[Card]:
    return [Card(v) for v in range(1, 105)]


def _find_player(state: GameState, player_id: PlayerID) -> Player:
    for player in state.players:
        if player.player_id == player_id:
            return player
    raise ValueError(f"unknown player_id: {player_id!r}")


def _row_index_by_id(state: GameState, row_id: RowID) -> int:
    for index, row in enumerate(state.rows):
        if row.row_id == row_id:
            return index
    raise ValueError(f"unknown row_id: {row_id!r}")


def _normalize_play_command(
    player_id: PlayerID,
    cmd: Card | PlayCardCommand,
) -> Card:
    if isinstance(cmd, Card):
        return cmd

    if isinstance(cmd, PlayCardCommand):
        if cmd.player_id != player_id:
            raise ValueError(
                f"PlayCardCommand player_id mismatch: expected {player_id!r}, got {cmd.player_id!r}"
            )
        return Card(cmd.card_value)

    raise TypeError(f"unsupported play selection type: {type(cmd)!r}")


def _normalize_choose_row_result(
    state: GameState,
    expected_player_id: PlayerID,
    result: RowID | ChooseRowCommand,
) -> RowID:
    if isinstance(result, ChooseRowCommand):
        if result.player_id != expected_player_id:
            raise ValueError(
                f"ChooseRowCommand player_id mismatch: expected {expected_player_id!r}, got {result.player_id!r}"
            )
        return result.row_id

    return result


def setup_game(
    player_list: Sequence[str],
    *,
    rng: random.Random | None = None,
    config: RulesConfig | None = None,
    hand_size: int | None = None,
) -> GameState:
    if rng is None:
        rng = random.Random()

    if not (2 <= len(player_list) <= 6):
        raise ValueError("player count must be 2..6")

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
    rows = [
        Row(row_id=RowID(f"row-{index}"))
        for index in range(config.row_count)
    ]

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
    state.resolve_order.clear()
    state.phase_info = PhaseInfo(
        phase=Phase.CHOOSE_CARD,
        message="Choose one card.",
    )


@dataclass(slots=True)
class StepResult:
    player_id: PlayerID
    card: Card
    action: str
    row_id: RowID
    points_gained: int


def resolve_round(
    state: GameState,
    selections: dict[PlayerID, Card | PlayCardCommand],
    choose_row: ChooseRowFn,
) -> list[StepResult]:
    expected_player_ids = {player.player_id for player in state.players}
    if set(selections.keys()) != expected_player_ids:
        raise ValueError("selections must contain one card for every player_id")

    state.phase_info = PhaseInfo(
        phase=Phase.REVEAL_AND_RESOLVE,
        message="Revealing cards and resolving trick.",
    )

    normalized: dict[PlayerID, Card] = {
        player_id: _normalize_play_command(player_id, selection)
        for player_id, selection in selections.items()
    }

    for player_id, card in normalized.items():
        player = _find_player(state, player_id)
        try:
            hand_index = next(
                index for index, hand_card in enumerate(player.hand)
                if hand_card.value == card.value
            )
        except StopIteration as exc:
            raise ValueError(
                f"player {player_id!r} does not have card {card.value}"
            ) from exc
        player.hand.pop(hand_index)

    state.selected_cards = dict(normalized)

    ordered = sorted(normalized.items(), key=lambda item: item[1].value)
    state.resolve_order = [player_id for player_id, _card in ordered]

    results: list[StepResult] = []

    for player_id, card in ordered:
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

            chosen = choose_row(state, player_id, card)
            chosen_row_id = _normalize_choose_row_result(
                state,
                player_id,
                chosen,
            )
            chosen_index = _row_index_by_id(state, chosen_row_id)

            points, _taken = take_row(state.rows, chosen_index)
            _find_player(state, player_id).score += points
            state.rows[chosen_index].cards = [card]

            results.append(
                StepResult(
                    player_id=player_id,
                    card=card,
                    action="took_row_small",
                    row_id=chosen_row_id,
                    points_gained=points,
                )
            )
            continue

        target_row = state.rows[row_index]
        points, taken = place_card(
            state.rows,
            row_index,
            card,
            row_capacity=state.config.row_capacity,
        )

        if taken is not None:
            _find_player(state, player_id).score += points
            action = "took_row_overflow"
        else:
            action = "placed"

        results.append(
            StepResult(
                player_id=player_id,
                card=card,
                action=action,
                row_id=target_row.row_id,
                points_gained=points,
            )
        )

    state.phase_info = PhaseInfo(
        phase=Phase.ROUND_SCORING,
        message="Trick finished.",
    )
    state.selected_cards.clear()
    state.resolve_order.clear()
    return results


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
