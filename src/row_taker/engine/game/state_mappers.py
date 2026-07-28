"""Serialization helpers for game state structures.

Public protocol messages should only cross the wire using immutable API types:
`Row`, `PublicState`, and `PlayerState`.

`GameState` serialization is kept as an explicit debug-only escape hatch for
`DebugStateSnapshot`. The mutable engine helpers used for that path stay private
inside this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import EngineRow, Player, PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo, StepAction
from row_taker.engine.game.state import (
    GameState,
    PlayerState,
    PublicState,
    RevealedPlay,
    RowChoiceRequired,
    RulesConfig,
    TrickResolutionCursor,
    TrickResolutionStep,
)
from row_taker.serialization.json_values import (
    JsonObject,
    require_field,
    require_int,
    require_object,
    require_sequence,
    require_str,
)


def _object_field(data: JsonObject, key: str, *, context: str) -> JsonObject:
    return require_object(require_field(data, key, context=context), context=f"{context}.{key}")


def _sequence_field(data: JsonObject, key: str, *, context: str) -> Sequence[object]:
    return require_sequence(require_field(data, key, context=context), context=f"{context}.{key}")


def _cards_from_sequence(value: object, *, context: str) -> tuple[Card, ...]:
    values = require_sequence(value, context=context)
    return tuple(
        card_from_dict(require_object(item, context=f"{context}[{index}]"))
        for index, item in enumerate(values)
    )


def card_to_dict(card: Card) -> dict[str, int]:
    return {"value": card.value}


def card_from_dict(data: Mapping[str, object]) -> Card:
    context = "card"
    return Card(require_int(require_field(data, "value", context=context), context="card.value"))


def rules_config_to_dict(config: RulesConfig) -> dict[str, int]:
    return {
        "hand_size": config.hand_size,
        "row_count": config.row_count,
        "row_capacity": config.row_capacity,
        "end_score": config.end_score,
    }


def rules_config_from_dict(data: Mapping[str, object]) -> RulesConfig:
    context = "rules_config"
    return RulesConfig(
        hand_size=require_int(
            require_field(data, "hand_size", context=context), context="rules_config.hand_size"
        ),
        row_count=require_int(
            require_field(data, "row_count", context=context), context="rules_config.row_count"
        ),
        row_capacity=require_int(
            require_field(data, "row_capacity", context=context),
            context="rules_config.row_capacity",
        ),
        end_score=require_int(
            require_field(data, "end_score", context=context), context="rules_config.end_score"
        ),
    )


def public_player_info_to_dict(player: PublicPlayerInfo) -> dict[str, object]:
    return {
        "player_id": str(player.player_id),
        "name": player.name,
        "score": player.score,
        "hand_count": player.hand_count,
    }


def public_player_info_from_dict(data: Mapping[str, object]) -> PublicPlayerInfo:
    context = "public_player"
    return PublicPlayerInfo(
        player_id=PlayerID(
            require_str(
                require_field(data, "player_id", context=context),
                context="public_player.player_id",
            )
        ),
        name=require_str(
            require_field(data, "name", context=context), context="public_player.name"
        ),
        score=require_int(
            require_field(data, "score", context=context), context="public_player.score"
        ),
        hand_count=require_int(
            require_field(data, "hand_count", context=context),
            context="public_player.hand_count",
        ),
    )


def row_to_dict(row: Row) -> dict[str, object]:
    return {
        "row_id": str(row.row_id),
        "cards": [card_to_dict(card) for card in row.cards],
    }


def row_from_dict(data: Mapping[str, object]) -> Row:
    context = "row"
    return Row(
        row_id=RowID(
            require_str(require_field(data, "row_id", context=context), context="row.row_id")
        ),
        cards=_cards_from_sequence(
            require_field(data, "cards", context=context), context="row.cards"
        ),
    )


def phase_info_to_dict(phase_info: PhaseInfo) -> dict[str, object]:
    return {
        "phase": phase_info.phase.value,
        "active_player_id": None
        if phase_info.active_player_id is None
        else str(phase_info.active_player_id),
        "pending_card": None
        if phase_info.pending_card is None
        else card_to_dict(phase_info.pending_card),
        "selectable_row_ids": [str(row_id) for row_id in phase_info.selectable_row_ids],
        "message": phase_info.message,
    }


def phase_info_from_dict(data: Mapping[str, object]) -> PhaseInfo:
    context = "phase_info"
    active_player_value = require_field(data, "active_player_id", context=context)
    pending_card_value = require_field(data, "pending_card", context=context)
    selectable_values = _sequence_field(data, "selectable_row_ids", context=context)
    return PhaseInfo(
        phase=Phase(
            require_str(require_field(data, "phase", context=context), context="phase_info.phase")
        ),
        active_player_id=None
        if active_player_value is None
        else PlayerID(require_str(active_player_value, context="phase_info.active_player_id")),
        pending_card=None
        if pending_card_value is None
        else card_from_dict(require_object(pending_card_value, context="phase_info.pending_card")),
        selectable_row_ids=tuple(
            RowID(require_str(value, context=f"phase_info.selectable_row_ids[{index}]"))
            for index, value in enumerate(selectable_values)
        ),
        message=require_str(
            require_field(data, "message", context=context), context="phase_info.message"
        ),
    )


def public_state_to_dict(state: PublicState) -> dict[str, object]:
    return {
        "config": rules_config_to_dict(state.config),
        "players": [public_player_info_to_dict(player) for player in state.players],
        "rows": [row_to_dict(row) for row in state.rows],
        "round_no": state.round_no,
        "trick_no": state.trick_no,
        "phase_info": phase_info_to_dict(state.phase_info),
    }


def public_state_from_dict(data: Mapping[str, object]) -> PublicState:
    context = "public_state"
    players_data = _sequence_field(data, "players", context=context)
    rows_data = _sequence_field(data, "rows", context=context)
    return PublicState(
        config=rules_config_from_dict(_object_field(data, "config", context=context)),
        players=tuple(
            public_player_info_from_dict(
                require_object(player, context=f"public_state.players[{index}]")
            )
            for index, player in enumerate(players_data)
        ),
        rows=tuple(
            row_from_dict(require_object(row, context=f"public_state.rows[{index}]"))
            for index, row in enumerate(rows_data)
        ),
        round_no=require_int(
            require_field(data, "round_no", context=context), context="public_state.round_no"
        ),
        trick_no=require_int(
            require_field(data, "trick_no", context=context), context="public_state.trick_no"
        ),
        phase_info=phase_info_from_dict(_object_field(data, "phase_info", context=context)),
    )


def player_state_to_dict(state: PlayerState) -> dict[str, object]:
    return {
        "public_state": public_state_to_dict(state.public_state),
        "self_player_id": str(state.self_player_id),
        "hand": [card_to_dict(card) for card in state.hand],
    }


def player_state_from_dict(data: Mapping[str, object]) -> PlayerState:
    context = "player_state"
    return PlayerState(
        public_state=public_state_from_dict(_object_field(data, "public_state", context=context)),
        self_player_id=PlayerID(
            require_str(
                require_field(data, "self_player_id", context=context),
                context="player_state.self_player_id",
            )
        ),
        hand=_cards_from_sequence(
            require_field(data, "hand", context=context), context="player_state.hand"
        ),
    )


def trick_resolution_step_to_dict(step: TrickResolutionStep) -> dict[str, object]:
    return {
        "action": step.action.value,
        "player_id": str(step.player_id),
        "affected_row_id": str(step.affected_row_id),
        "played_card": card_to_dict(step.played_card),
        "taken_cards": [card_to_dict(card) for card in step.taken_cards],
        "points_gained": step.points_gained,
        "new_row_cards": [card_to_dict(card) for card in step.new_row_cards],
    }


def trick_resolution_step_from_dict(data: Mapping[str, object]) -> TrickResolutionStep:
    context = "trick_resolution_step"
    return TrickResolutionStep(
        action=StepAction(
            require_str(require_field(data, "action", context=context), context=f"{context}.action")
        ),
        player_id=PlayerID(
            require_str(
                require_field(data, "player_id", context=context), context=f"{context}.player_id"
            )
        ),
        affected_row_id=RowID(
            require_str(
                require_field(data, "affected_row_id", context=context),
                context=f"{context}.affected_row_id",
            )
        ),
        played_card=card_from_dict(_object_field(data, "played_card", context=context)),
        taken_cards=_cards_from_sequence(
            require_field(data, "taken_cards", context=context), context=f"{context}.taken_cards"
        ),
        points_gained=require_int(
            require_field(data, "points_gained", context=context),
            context=f"{context}.points_gained",
        ),
        new_row_cards=_cards_from_sequence(
            require_field(data, "new_row_cards", context=context),
            context=f"{context}.new_row_cards",
        ),
    )


def _player_to_dict(player: Player) -> dict[str, object]:
    return {
        "player_id": str(player.player_id),
        "name": player.name,
        "hand": [card_to_dict(card) for card in player.hand],
        "score": player.score,
    }


def _player_from_dict(data: Mapping[str, object]) -> Player:
    context = "player"
    return Player(
        player_id=PlayerID(
            require_str(
                require_field(data, "player_id", context=context), context="player.player_id"
            )
        ),
        name=require_str(require_field(data, "name", context=context), context="player.name"),
        hand=list(
            _cards_from_sequence(
                require_field(data, "hand", context=context), context="player.hand"
            )
        ),
        score=require_int(require_field(data, "score", context=context), context="player.score"),
    )


def _engine_row_to_dict(row: EngineRow) -> dict[str, object]:
    return {
        "row_id": str(row.row_id),
        "cards": [card_to_dict(card) for card in row.cards],
    }


def _engine_row_from_dict(data: Mapping[str, object]) -> EngineRow:
    context = "engine_row"
    return EngineRow(
        row_id=RowID(
            require_str(require_field(data, "row_id", context=context), context="engine_row.row_id")
        ),
        cards=list(
            _cards_from_sequence(
                require_field(data, "cards", context=context), context="engine_row.cards"
            )
        ),
    )


def _revealed_play_to_dict(play: RevealedPlay) -> dict[str, object]:
    return {
        "player_id": str(play.player_id),
        "card": card_to_dict(play.card),
    }


def _revealed_play_from_dict(data: Mapping[str, object]) -> RevealedPlay:
    context = "revealed_play"
    return RevealedPlay(
        player_id=PlayerID(
            require_str(
                require_field(data, "player_id", context=context),
                context="revealed_play.player_id",
            )
        ),
        card=card_from_dict(_object_field(data, "card", context=context)),
    )


def _row_choice_required_to_dict(prompt: RowChoiceRequired) -> dict[str, object]:
    return {
        "player_id": str(prompt.player_id),
        "card": card_to_dict(prompt.card),
        "selectable_row_ids": [str(row_id) for row_id in prompt.selectable_row_ids],
    }


def _row_choice_required_from_dict(data: Mapping[str, object]) -> RowChoiceRequired:
    context = "row_choice_required"
    selectable_values = _sequence_field(data, "selectable_row_ids", context=context)
    return RowChoiceRequired(
        player_id=PlayerID(
            require_str(
                require_field(data, "player_id", context=context),
                context="row_choice_required.player_id",
            )
        ),
        card=card_from_dict(_object_field(data, "card", context=context)),
        selectable_row_ids=tuple(
            RowID(require_str(value, context=f"row_choice_required.selectable_row_ids[{index}]"))
            for index, value in enumerate(selectable_values)
        ),
    )


def _trick_resolution_cursor_to_dict(cursor: TrickResolutionCursor) -> dict[str, object]:
    return {
        "remaining_player_ids": [str(player_id) for player_id in cursor.remaining_player_ids],
        "steps": [trick_resolution_step_to_dict(step) for step in cursor.steps],
    }


def _trick_resolution_cursor_from_dict(data: Mapping[str, object]) -> TrickResolutionCursor:
    context = "trick_resolution_cursor"
    remaining_values = _sequence_field(data, "remaining_player_ids", context=context)
    step_values = _sequence_field(data, "steps", context=context)
    return TrickResolutionCursor(
        remaining_player_ids=[
            PlayerID(require_str(value, context=f"{context}.remaining_player_ids[{index}]"))
            for index, value in enumerate(remaining_values)
        ],
        steps=[
            trick_resolution_step_from_dict(
                require_object(value, context=f"{context}.steps[{index}]")
            )
            for index, value in enumerate(step_values)
        ],
    )


def game_state_to_dict(state: GameState) -> dict[str, object]:
    return {
        "config": rules_config_to_dict(state.config),
        "players": [_player_to_dict(player) for player in state.players],
        "rows": [_engine_row_to_dict(row) for row in state.rows],
        "deck": [card_to_dict(card) for card in state.deck],
        "round_no": state.round_no,
        "trick_no": state.trick_no,
        "phase_info": phase_info_to_dict(state.phase_info),
        "selected_cards": [
            {"player_id": str(player_id), "card": card_to_dict(card)}
            for player_id, card in state.selected_cards.items()
        ],
        "current_trick_revealed_plays": [
            _revealed_play_to_dict(play) for play in state.current_trick_revealed_plays
        ],
        "resolution_cursor": None
        if state.resolution_cursor is None
        else _trick_resolution_cursor_to_dict(state.resolution_cursor),
    }


def game_state_from_dict(data: Mapping[str, object]) -> GameState:
    context = "game_state"
    players_data = _sequence_field(data, "players", context=context)
    rows_data = _sequence_field(data, "rows", context=context)
    deck_data = _sequence_field(data, "deck", context=context)
    selected_cards_data = _sequence_field(data, "selected_cards", context=context)
    revealed_data = _sequence_field(data, "current_trick_revealed_plays", context=context)
    state = GameState(
        config=rules_config_from_dict(_object_field(data, "config", context=context)),
        players=[
            _player_from_dict(require_object(player, context=f"game_state.players[{index}]"))
            for index, player in enumerate(players_data)
        ],
        rows=[
            _engine_row_from_dict(require_object(row, context=f"game_state.rows[{index}]"))
            for index, row in enumerate(rows_data)
        ],
        deck=[
            card_from_dict(require_object(card, context=f"game_state.deck[{index}]"))
            for index, card in enumerate(deck_data)
        ],
        round_no=require_int(
            require_field(data, "round_no", context=context), context="game_state.round_no"
        ),
        trick_no=require_int(
            require_field(data, "trick_no", context=context), context="game_state.trick_no"
        ),
        phase_info=phase_info_from_dict(_object_field(data, "phase_info", context=context)),
    )
    selected_cards: dict[PlayerID, Card] = {}
    for index, value in enumerate(selected_cards_data):
        entry_context = f"game_state.selected_cards[{index}]"
        entry = require_object(value, context=entry_context)
        player_id = PlayerID(
            require_str(
                require_field(entry, "player_id", context=entry_context),
                context=f"{entry_context}.player_id",
            )
        )
        selected_cards[player_id] = card_from_dict(
            require_object(
                require_field(entry, "card", context=entry_context),
                context=f"{entry_context}.card",
            )
        )
    state.selected_cards = selected_cards
    state.current_trick_revealed_plays = tuple(
        _revealed_play_from_dict(
            require_object(play, context=f"game_state.current_trick_revealed_plays[{index}]")
        )
        for index, play in enumerate(revealed_data)
    )
    resolution_cursor = require_field(data, "resolution_cursor", context=context)
    state.resolution_cursor = (
        None
        if resolution_cursor is None
        else _trick_resolution_cursor_from_dict(
            require_object(resolution_cursor, context="game_state.resolution_cursor")
        )
    )
    return state


__all__ = [
    "card_from_dict",
    "card_to_dict",
    "game_state_from_dict",
    "game_state_to_dict",
    "phase_info_from_dict",
    "phase_info_to_dict",
    "player_state_from_dict",
    "player_state_to_dict",
    "public_player_info_from_dict",
    "public_player_info_to_dict",
    "public_state_from_dict",
    "public_state_to_dict",
    "row_from_dict",
    "row_to_dict",
    "rules_config_from_dict",
    "rules_config_to_dict",
    "trick_resolution_step_from_dict",
    "trick_resolution_step_to_dict",
]
