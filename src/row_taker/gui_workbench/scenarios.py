from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from row_taker.client.core_reducer import (
    advance_presentation_queue,
    reduce_server_message,
)
from row_taker.client.core_state import ClientCoreState, ClientMode, PendingAction
from row_taker.client.presentation_events import PresentationEvent
from row_taker.client.state import ClientState
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PlayerState, PublicState, RulesConfig
from row_taker.protocol.messages import (
    CardsRevealed,
    ChooseRowRequested,
    PlayedCardView,
    RowChoiceCommitted,
)

DEFAULT_SIZE = (1600, 900)
ANIMATION_FRAMES = (0, 8, 16, 24, 32)


@dataclass(frozen=True, slots=True)
class WorkbenchScenario:
    """A deterministic input fixture for the production ``GameFrame``.

    The scenario owns no rendering information. It only supplies the same
    ``ClientState`` and timing inputs that the live GUI passes to ``GameFrame``.
    """

    name: str
    description: str
    state: ClientState
    default_size: tuple[int, int] = DEFAULT_SIZE
    interesting_frames: tuple[int, ...] = (0,)
    last_action_summary: str = "GUI-Workbench: deterministisches Szenario."


ScenarioFactory = Callable[[], WorkbenchScenario]


def _base_state(
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
    hand = tuple(Card(value) for value in (7, 17, 28, 39, 44, 53, 62, 71, 86, 101))

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
        message=(
            "Choose a row to take."
            if phase == Phase.CHOOSE_ROW
            else "Choose one card."
        ),
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


def _revealed_state(
    plays: tuple[tuple[int, int], ...],
    *,
    rows: tuple[Row, ...] | None = None,
) -> ClientState:
    state = _base_state(rows=rows)
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



def _with_choose_row_request(state: ClientState) -> ClientState:
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


def _advance_to_event(
    state: ClientState,
    event_type: type[PresentationEvent],
) -> ClientState:
    current = state
    while current.pending_presentation_steps:
        if isinstance(current.pending_presentation_steps[0].event, event_type):
            return current
        current = advance_presentation_queue(current)
    raise ValueError(f"scenario could not find pending event {event_type.__name__}")


def _choose_card() -> WorkbenchScenario:
    return WorkbenchScenario(
        name="choose-card",
        description="Ruhiger Spielzustand mit auswählbarer eigener Hand.",
        state=_base_state(),
    )


def _choose_row() -> WorkbenchScenario:
    base = _base_state()
    assert base.public_state is not None
    row_ids = tuple(row.row_id for row in base.public_state.rows)
    return WorkbenchScenario(
        name="choose-row",
        description="Eigener Spieler muss für die kleinste Karte eine Reihe wählen.",
        state=_base_state(
            phase=Phase.CHOOSE_ROW,
            pending_action=PendingAction.CHOOSE_ROW,
            pending_card=Card(7),
            selectable_row_ids=row_ids,
        ),
    )


def _cards_revealed() -> WorkbenchScenario:
    return WorkbenchScenario(
        name="cards-revealed",
        description="Vier Karten sind aufgedeckt; der erste Präsentationsschritt läuft.",
        state=_revealed_state(((0, 44), (1, 62), (2, 71), (3, 86))),
        interesting_frames=ANIMATION_FRAMES,
    )


def _card_placed() -> WorkbenchScenario:
    from row_taker.client.presentation_events import PresentationCardPlaced

    state = _advance_to_event(
        _revealed_state(((0, 44), (1, 62), (2, 71), (3, 86))),
        PresentationCardPlaced,
    )
    return WorkbenchScenario(
        name="card-placed",
        description="Eine aufgedeckte Karte bewegt sich in ihre Zielreihe.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )


def _row_choice_required() -> WorkbenchScenario:
    from row_taker.client.presentation_events import PresentationRowChoiceRequired

    state = _with_choose_row_request(_revealed_state(((0, 7),)))
    state = _advance_to_event(state, PresentationRowChoiceRequired)
    return WorkbenchScenario(
        name="row-choice-required",
        description="Die kleinste Karte wartet auf eine externe Reihenwahl.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )


def _row_taken() -> WorkbenchScenario:
    from row_taker.client.presentation_events import PresentationRowTaken

    state = _with_choose_row_request(_revealed_state(((0, 7),)))
    assert state.public_state is not None
    state = reduce_server_message(
        state,
        RowChoiceCommitted(row_id=state.public_state.rows[1].row_id),
    )
    state = _advance_to_event(state, PresentationRowTaken)
    return WorkbenchScenario(
        name="row-taken",
        description="Eine gewählte Reihe wird genommen und durch die kleine Karte ersetzt.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )


def _overflow_resolved() -> WorkbenchScenario:
    from row_taker.client.presentation_events import PresentationOverflowResolved

    rows = (
        Row(RowID("row-0"), tuple(Card(value) for value in (10, 20, 30, 40, 50))),
        Row(RowID("row-1"), (Card(65),)),
        Row(RowID("row-2"), (Card(78),)),
        Row(RowID("row-3"), (Card(92),)),
    )
    state = _advance_to_event(
        _revealed_state(((0, 53),), rows=rows),
        PresentationOverflowResolved,
    )
    return WorkbenchScenario(
        name="overflow-resolved",
        description="Eine sechste Karte löst einen Reihenüberlauf aus.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )


def _long_names() -> WorkbenchScenario:
    return WorkbenchScenario(
        name="long-names",
        description="Layout-Grenzfall mit langen Spielernamen.",
        state=_base_state(
            player_names=(
                "Ada mit einem ungewöhnlich langen Namen",
                "Benedikt-von-der-Testspielrunde",
                "Clara Beispielspielerin",
                "Dorian der Unerschrockene",
            )
        ),
    )


_SCENARIO_FACTORIES: dict[str, ScenarioFactory] = {
    "choose-card": _choose_card,
    "choose-row": _choose_row,
    "cards-revealed": _cards_revealed,
    "card-placed": _card_placed,
    "row-choice-required": _row_choice_required,
    "row-taken": _row_taken,
    "overflow-resolved": _overflow_resolved,
    "long-names": _long_names,
}


def scenario_names() -> tuple[str, ...]:
    return tuple(_SCENARIO_FACTORIES)


def get_scenario(name: str) -> WorkbenchScenario:
    try:
        factory = _SCENARIO_FACTORIES[name]
    except KeyError as exc:
        available = ", ".join(scenario_names())
        raise KeyError(f"unknown workbench scenario {name!r}; available: {available}") from exc
    return factory()


def scenarios() -> tuple[WorkbenchScenario, ...]:
    return tuple(factory() for factory in _SCENARIO_FACTORIES.values())
