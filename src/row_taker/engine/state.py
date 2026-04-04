from dataclasses import dataclass, field

from .models import Card, Player, PlayerID, PublicPlayerInfo, Row
from .phases import Phase, PhaseInfo


@dataclass(frozen=True, slots=True)
class RulesConfig:
    hand_size: int = 10
    row_count: int = 4
    row_capacity: int = 5
    end_score: int = 66


@dataclass(slots=True)
class GameState:
    config: RulesConfig
    players: list[Player]
    rows: list[Row]
    deck: list[Card]

    round_no: int = 1
    trick_no: int = 1

    phase_info: PhaseInfo = field(
        default_factory=lambda: PhaseInfo(phase=Phase.ROUND_SETUP)
    )

    selected_cards: dict[PlayerID, Card] = field(default_factory=dict)
    resolve_order: list[PlayerID] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class PlayerState:
    config: RulesConfig
    self_player_id: PlayerID

    players: list[PublicPlayerInfo]
    rows: list[Row]
    hand: list[Card]

    round_no: int
    trick_no: int
    phase_info: PhaseInfo
