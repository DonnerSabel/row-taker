from __future__ import annotations

from dataclasses import replace

from row_taker.client.core_reducer import reduce_server_message
from row_taker.client.core_state import PendingAction
from row_taker.client.presentation_events import (
    PresentationGameFinished,
    PresentationRoundFinished,
)
from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.state import UiMessage
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import Row, RowID
from row_taker.engine.game.phases import Phase
from row_taker.gui_workbench.scenario_builders import (
    advance_to_event,
    build_game_state,
    build_revealed_state,
    with_choose_row_request,
)
from row_taker.gui_workbench.scenario_types import (
    ANIMATION_FRAMES,
    GameWorkbenchScenario,
    ScenarioFactory,
)
from row_taker.protocol.messages import RowChoiceCommitted

SIX_PLAYER_NAMES = ("Ada", "Ben", "Clara", "Dorian", "Emil", "Fatima")
SIX_PLAYER_PLAYS = ((0, 44), (1, 62), (2, 71), (3, 86), (4, 90), (5, 100))

def _choose_card() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="choose-card",
        description="Ruhiger Spielzustand mit auswählbarer eigener Hand.",
        state=build_game_state(),
    )
def _choose_row() -> GameWorkbenchScenario:
    base = build_game_state()
    assert base.public_state is not None
    row_ids = tuple(row.row_id for row in base.public_state.rows)
    return GameWorkbenchScenario(
        name="choose-row",
        description="Eigener Spieler muss für die kleinste Karte eine Reihe wählen.",
        state=build_game_state(
            phase=Phase.CHOOSE_ROW,
            pending_action=PendingAction.CHOOSE_ROW,
            pending_card=Card(7),
            selectable_row_ids=row_ids,
        ),
    )
def _cards_revealed() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="cards-revealed",
        description="Vier Karten sind aufgedeckt; der erste Präsentationsschritt läuft.",
        state=build_revealed_state(((0, 44), (1, 62), (2, 71), (3, 86))),
        interesting_frames=ANIMATION_FRAMES,
    )
def _card_placed() -> GameWorkbenchScenario:
    from row_taker.client.presentation_events import PresentationCardPlaced

    state = advance_to_event(
        build_revealed_state(((0, 44), (1, 62), (2, 71), (3, 86))),
        PresentationCardPlaced,
    )
    return GameWorkbenchScenario(
        name="card-placed",
        description="Eine aufgedeckte Karte bewegt sich in ihre Zielreihe.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )
def _row_choice_required() -> GameWorkbenchScenario:
    from row_taker.client.presentation_events import PresentationRowChoiceRequired

    state = with_choose_row_request(build_revealed_state(((0, 7),)))
    state = advance_to_event(state, PresentationRowChoiceRequired)
    return GameWorkbenchScenario(
        name="row-choice-required",
        description="Die kleinste Karte wartet auf eine externe Reihenwahl.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )
def _row_taken() -> GameWorkbenchScenario:
    from row_taker.client.presentation_events import PresentationRowTaken

    state = with_choose_row_request(build_revealed_state(((0, 7),)))
    assert state.public_state is not None
    state = reduce_server_message(
        state,
        RowChoiceCommitted(row_id=state.public_state.rows[1].row_id),
    )
    state = advance_to_event(state, PresentationRowTaken)
    return GameWorkbenchScenario(
        name="row-taken",
        description="Eine gewählte Reihe wird genommen und durch die kleine Karte ersetzt.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )
def _overflow_resolved() -> GameWorkbenchScenario:
    from row_taker.client.presentation_events import PresentationOverflowResolved

    rows = (
        Row(RowID("row-0"), tuple(Card(value) for value in (10, 20, 30, 40, 50))),
        Row(RowID("row-1"), (Card(65),)),
        Row(RowID("row-2"), (Card(78),)),
        Row(RowID("row-3"), (Card(92),)),
    )
    state = advance_to_event(
        build_revealed_state(((0, 53),), rows=rows),
        PresentationOverflowResolved,
    )
    return GameWorkbenchScenario(
        name="overflow-resolved",
        description="Eine sechste Karte löst einen Reihenüberlauf aus.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )
def _five_opponents() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="five-opponents",
        description="Maximale Besetzung mit fünf kompakten Gegnerkacheln.",
        state=build_game_state(player_names=SIX_PLAYER_NAMES),
    )
def _five_opponents_revealed() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="five-opponents-revealed",
        description="Fünf überlappende Gegnerkarten und die eigene Karte sind aufgedeckt.",
        state=build_revealed_state(SIX_PLAYER_PLAYS, player_names=SIX_PLAYER_NAMES),
        interesting_frames=ANIMATION_FRAMES,
    )
def _five_opponents_active() -> GameWorkbenchScenario:
    from row_taker.client.presentation_events import PresentationCardPlaced

    state = advance_to_event(
        build_revealed_state(SIX_PLAYER_PLAYS, player_names=SIX_PLAYER_NAMES),
        PresentationCardPlaced,
    )
    return GameWorkbenchScenario(
        name="five-opponents-active",
        description="Maximale Besetzung mit hervorgehobener aktiver Spielerkachel.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )
def _own_player_active() -> GameWorkbenchScenario:
    scenario = _row_choice_required()
    return GameWorkbenchScenario(
        name="own-player-active",
        description="Die eigene Kachel ist während der Reihenwahl aktiv.",
        state=scenario.state,
        interesting_frames=scenario.interesting_frames,
    )
def _own_card_revealed() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="own-card-revealed",
        description="Die eigene aufgedeckte Karte liegt ausschließlich an der eigenen Kachel.",
        state=build_revealed_state(((0, 44),)),
        interesting_frames=ANIMATION_FRAMES,
    )
def _presentation_click_required() -> GameWorkbenchScenario:
    scenario = _cards_revealed()
    return GameWorkbenchScenario(
        name="presentation-click-required",
        description="Wartender Präsentationsschritt mit globalem Klickhinweis.",
        state=scenario.state,
        interesting_frames=(0,),
    )
def _long_names_five_opponents() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="long-names-five-opponents",
        description="Maximale Besetzung mit sechs langen Spielernamen.",
        state=build_game_state(
            player_names=(
                "Ada mit einem ungewöhnlich langen Namen",
                "Benedikt-von-der-Testspielrunde",
                "Clara Beispielspielerin",
                "Dorian der Unerschrockene",
                "Emil mit einem ebenfalls sehr langen Namen",
                "Fatima aus der maximal besetzten Testspielrunde",
            )
        ),
    )
def _error_message() -> GameWorkbenchScenario:
    state = build_game_state()
    state = replace(
        state,
        feedback_state=replace(
            state.feedback_state,
            flash_message=UiMessage(
                level="error",
                text="Ungültige Karte: Bitte eine sichtbare Handkarte auswählen.",
            ),
        ),
    )
    return GameWorkbenchScenario(
        name="error-message",
        description="Echte Fehlermeldung innerhalb der eigenen Spielerkachel.",
        state=state,
    )
def _finished_scenario(
    *,
    name: str,
    description: str,
    event: PresentationRoundFinished | PresentationGameFinished,
) -> GameWorkbenchScenario:
    state = build_game_state(pending_action=PendingAction.NONE)
    public_state = state.public_state
    if public_state is None:
        raise ValueError("finished workbench scenario requires a public state")
    step = PresentationStep(
        event=event,
        public_state_before=public_state,
        public_state_after=public_state,
    )
    state = replace(
        state,
        core_state=replace(
            state.core_state,
            presentation_steps=(step,),
            pending_presentation_steps=(step,),
        ),
    )
    return GameWorkbenchScenario(
        name=name,
        description=description,
        state=state,
    )
def _round_finished() -> GameWorkbenchScenario:
    return _finished_scenario(
        name="round-finished",
        description="Rundenende als Meldung innerhalb der eigenen Spielerkachel.",
        event=PresentationRoundFinished(),
    )
def _game_finished() -> GameWorkbenchScenario:
    return _finished_scenario(
        name="game-finished",
        description="Spielende als Meldung innerhalb der eigenen Spielerkachel.",
        event=PresentationGameFinished(),
    )
def _long_names() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="long-names",
        description="Layout-Grenzfall mit langen Spielernamen.",
        state=build_game_state(
            player_names=(
                "Ada mit einem ungewöhnlich langen Namen",
                "Benedikt-von-der-Testspielrunde",
                "Clara Beispielspielerin",
                "Dorian der Unerschrockene",
            )
        ),
    )

GAME_SCENARIO_FACTORIES: dict[str, ScenarioFactory] = {
    "choose-card": _choose_card,
    "choose-row": _choose_row,
    "cards-revealed": _cards_revealed,
    "card-placed": _card_placed,
    "row-choice-required": _row_choice_required,
    "row-taken": _row_taken,
    "overflow-resolved": _overflow_resolved,
    "long-names": _long_names,
    "five-opponents": _five_opponents,
    "five-opponents-revealed": _five_opponents_revealed,
    "five-opponents-active": _five_opponents_active,
    "own-player-active": _own_player_active,
    "own-card-revealed": _own_card_revealed,
    "presentation-click-required": _presentation_click_required,
    "long-names-five-opponents": _long_names_five_opponents,
    "error-message": _error_message,
    "round-finished": _round_finished,
    "game-finished": _game_finished,
}
