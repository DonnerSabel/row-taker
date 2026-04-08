from __future__ import annotations

from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import DeltaPublicState, PlayerState, PublicState, RulesConfig


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
        "active_player_id": None
        if phase_info.active_player_id is None
        else str(phase_info.active_player_id),
        "pending_card": None
        if phase_info.pending_card is None
        else card_to_dict(phase_info.pending_card),
        "selectable_row_ids": [str(row_id) for row_id in phase_info.selectable_row_ids],
        "message": phase_info.message,
    }


def phase_info_from_dict(data: dict[str, object]) -> PhaseInfo:
    return PhaseInfo(
        phase=Phase(str(data["phase"])),
        active_player_id=None
        if data["active_player_id"] is None
        else PlayerID(str(data["active_player_id"])),
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


def delta_public_state_to_dict(delta: DeltaPublicState) -> dict[str, object]:
    return {
        "player_id": str(delta.player_id),
        "affected_row_id": str(delta.affected_row_id),
        "new_row_cards": [card_to_dict(card) for card in delta.new_row_cards],
    }


def delta_public_state_from_dict(data: dict[str, object]) -> DeltaPublicState:
    return DeltaPublicState(
        player_id=PlayerID(str(data["player_id"])),
        affected_row_id=RowID(str(data["affected_row_id"])),
        new_row_cards=tuple(card_from_dict(card) for card in data["new_row_cards"]),
    )
