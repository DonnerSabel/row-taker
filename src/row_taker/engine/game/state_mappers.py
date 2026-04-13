from __future__ import annotations

from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo, StepAction
from row_taker.engine.game.models import Player
from row_taker.engine.game.state import (
    GameState,
    PlayerState,
    PublicState,
    RevealedPlay,
    RulesConfig,
    RowChoiceRequired,
    TrickResolutionCursor,
    TrickResolutionStep,
)


def card_to_dict(card: Card) -> dict[str, int]:
    return {"value": card.value}


def card_from_dict(data: dict[str, int]) -> Card:
    return Card(data["value"])


def rules_config_to_dict(config: RulesConfig) -> dict[str, int]:
    return {
        "hand_size": config.hand_size,
        "row_count": config.row_count,
        "row_capacity": config.row_capacity,
        "end_score": config.end_score,
    }


def rules_config_from_dict(data: dict[str, int]) -> RulesConfig:
    return RulesConfig(
        hand_size=data["hand_size"],
        row_count=data["row_count"],
        row_capacity=data["row_capacity"],
        end_score=data["end_score"],
    )


def public_player_info_to_dict(player: PublicPlayerInfo) -> dict[str, object]:
    return {
        "player_id": str(player.player_id),
        "name": player.name,
        "score": player.score,
        "hand_count": player.hand_count,
    }


def public_player_info_from_dict(data: dict[str, object]) -> PublicPlayerInfo:
    return PublicPlayerInfo(
        player_id=PlayerID(str(data["player_id"])),
        name=str(data["name"]),
        score=int(data["score"]),
        hand_count=int(data["hand_count"]),
    )


def row_to_dict(row: Row) -> dict[str, object]:
    return {
        "row_id": str(row.row_id),
        "cards": [card_to_dict(card) for card in row.cards],
    }


def row_from_dict(data: dict[str, object]) -> Row:
    return Row(
        row_id=RowID(str(data["row_id"])),
        cards=[card_from_dict(card) for card in data["cards"]],
    )


def phase_info_to_dict(phase_info: PhaseInfo) -> dict[str, object]:
    return {
        "phase": phase_info.phase.value,
        "active_player_id": None if phase_info.active_player_id is None else str(phase_info.active_player_id),
        "pending_card": None if phase_info.pending_card is None else card_to_dict(phase_info.pending_card),
        "selectable_row_ids": [str(row_id) for row_id in phase_info.selectable_row_ids],
        "message": phase_info.message,
    }


def phase_info_from_dict(data: dict[str, object]) -> PhaseInfo:
    return PhaseInfo(
        phase=Phase(str(data["phase"])),
        active_player_id=None if data["active_player_id"] is None else PlayerID(str(data["active_player_id"])),
        pending_card=None if data["pending_card"] is None else card_from_dict(data["pending_card"]),
        selectable_row_ids=tuple(RowID(str(row_id)) for row_id in data["selectable_row_ids"]),
        message=str(data["message"]),
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


def public_state_from_dict(data: dict[str, object]) -> PublicState:
    return PublicState(
        config=rules_config_from_dict(data["config"]),
        players=[public_player_info_from_dict(player) for player in data["players"]],
        rows=[row_from_dict(row) for row in data["rows"]],
        round_no=int(data["round_no"]),
        trick_no=int(data["trick_no"]),
        phase_info=phase_info_from_dict(data["phase_info"]),
    )


def player_state_to_dict(state: PlayerState) -> dict[str, object]:
    return {
        "public_state": public_state_to_dict(state.public_state),
        "self_player_id": str(state.self_player_id),
        "hand": [card_to_dict(card) for card in state.hand],
    }


def player_state_from_dict(data: dict[str, object]) -> PlayerState:
    return PlayerState(
        public_state=public_state_from_dict(data["public_state"]),
        self_player_id=PlayerID(str(data["self_player_id"])),
        hand=[card_from_dict(card) for card in data["hand"]],
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


def trick_resolution_step_from_dict(data: dict[str, object]) -> TrickResolutionStep:
    return TrickResolutionStep(
        action=StepAction(str(data["action"])),
        player_id=PlayerID(str(data["player_id"])),
        affected_row_id=RowID(str(data["affected_row_id"])),
        played_card=card_from_dict(data["played_card"]),
        taken_cards=tuple(card_from_dict(card) for card in data["taken_cards"]),
        points_gained=int(data["points_gained"]),
        new_row_cards=tuple(card_from_dict(card) for card in data["new_row_cards"]),
    )



def player_to_dict(player: Player) -> dict[str, object]:
    return {
        "player_id": str(player.player_id),
        "name": player.name,
        "hand": [card_to_dict(card) for card in player.hand],
        "score": player.score,
    }


def player_from_dict(data: dict[str, object]) -> Player:
    return Player(
        player_id=PlayerID(str(data["player_id"])),
        name=str(data["name"]),
        hand=[card_from_dict(card) for card in data["hand"]],
        score=int(data["score"]),
    )


def revealed_play_to_dict(play: RevealedPlay) -> dict[str, object]:
    return {
        "player_id": str(play.player_id),
        "card": card_to_dict(play.card),
    }


def revealed_play_from_dict(data: dict[str, object]) -> RevealedPlay:
    return RevealedPlay(
        player_id=PlayerID(str(data["player_id"])),
        card=card_from_dict(data["card"]),
    )


def row_choice_required_to_dict(prompt: RowChoiceRequired) -> dict[str, object]:
    return {
        "player_id": str(prompt.player_id),
        "card": card_to_dict(prompt.card),
        "selectable_row_ids": [str(row_id) for row_id in prompt.selectable_row_ids],
    }


def row_choice_required_from_dict(data: dict[str, object]) -> RowChoiceRequired:
    return RowChoiceRequired(
        player_id=PlayerID(str(data["player_id"])),
        card=card_from_dict(data["card"]),
        selectable_row_ids=tuple(RowID(str(row_id)) for row_id in data["selectable_row_ids"]),
    )


def trick_resolution_cursor_to_dict(cursor: TrickResolutionCursor) -> dict[str, object]:
    return {
        "remaining_player_ids": [str(player_id) for player_id in cursor.remaining_player_ids],
        "steps": [trick_resolution_step_to_dict(step) for step in cursor.steps],
    }


def trick_resolution_cursor_from_dict(data: dict[str, object]) -> TrickResolutionCursor:
    return TrickResolutionCursor(
        remaining_player_ids=[PlayerID(str(player_id)) for player_id in data["remaining_player_ids"]],
        steps=[trick_resolution_step_from_dict(step) for step in data["steps"]],
    )


def game_state_to_dict(state: GameState) -> dict[str, object]:
    return {
        "config": rules_config_to_dict(state.config),
        "players": [player_to_dict(player) for player in state.players],
        "rows": [row_to_dict(row) for row in state.rows],
        "deck": [card_to_dict(card) for card in state.deck],
        "round_no": state.round_no,
        "trick_no": state.trick_no,
        "phase_info": phase_info_to_dict(state.phase_info),
        "selected_cards": [
            {"player_id": str(player_id), "card": card_to_dict(card)}
            for player_id, card in state.selected_cards.items()
        ],
        "current_trick_revealed_plays": [revealed_play_to_dict(play) for play in state.current_trick_revealed_plays],
        "resolution_cursor": None if state.resolution_cursor is None else trick_resolution_cursor_to_dict(state.resolution_cursor),
    }


def game_state_from_dict(data: dict[str, object]) -> GameState:
    state = GameState(
        config=rules_config_from_dict(data["config"]),
        players=[player_from_dict(player) for player in data["players"]],
        rows=[row_from_dict(row) for row in data["rows"]],
        deck=[card_from_dict(card) for card in data["deck"]],
        round_no=int(data["round_no"]),
        trick_no=int(data["trick_no"]),
        phase_info=phase_info_from_dict(data["phase_info"]),
    )
    state.selected_cards = {
        PlayerID(str(entry["player_id"])): card_from_dict(entry["card"])
        for entry in data["selected_cards"]
    }
    state.current_trick_revealed_plays = tuple(
        revealed_play_from_dict(play) for play in data["current_trick_revealed_plays"]
    )
    resolution_cursor = data["resolution_cursor"]
    state.resolution_cursor = None if resolution_cursor is None else trick_resolution_cursor_from_dict(resolution_cursor)
    return state
