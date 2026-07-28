from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

from row_taker.client.core_reducer import (
    advance_presentation_queue,
    reduce_server_message,
)
from row_taker.client.core_state import ClientCoreState, ClientMode, PendingAction
from row_taker.client.presentation_events import (
    PresentationEvent,
    PresentationGameFinished,
    PresentationRoundFinished,
)
from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.state import (
    ClientState,
    UiMessage,
    enter_lobby_submenu,
    initial_client_state,
    with_navigation_updates,
)
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import PlayerID, PublicPlayerInfo, Row, RowID
from row_taker.engine.game.phases import Phase, PhaseInfo
from row_taker.engine.game.state import PlayerState, PublicState, RulesConfig
from row_taker.gui.connect_form_state import ConnectFormState
from row_taker.participants import ParticipantKind
from row_taker.protocol.messages import (
    CardsRevealed,
    ChooseRowRequested,
    IdentityAssigned,
    LobbyParticipantView,
    LobbySeatView,
    LobbyStateUpdated,
    LobbyView,
    PlayedCardView,
    RowChoiceCommitted,
)

DEFAULT_SIZE = (1600, 900)
ANIMATION_FRAMES = (0, 8, 16, 24, 32)
ScenarioCategory = Literal["connect", "lobby", "game"]


@dataclass(frozen=True, slots=True)
class ConnectWorkbenchScenario:
    """Deterministic input fixture for the production ``ConnectFrame``."""

    name: str
    description: str
    connect_form: ConnectFormState
    default_size: tuple[int, int] = DEFAULT_SIZE
    interesting_frames: tuple[int, ...] = (0,)


@dataclass(frozen=True, slots=True)
class LobbyWorkbenchScenario:
    """Deterministic input fixture for the production ``LobbyFrame``."""

    name: str
    description: str
    state: ClientState
    default_size: tuple[int, int] = DEFAULT_SIZE
    interesting_frames: tuple[int, ...] = (0,)


@dataclass(frozen=True, slots=True)
class GameWorkbenchScenario:
    """Deterministic input fixture for the production ``GameFrame``.

    The scenario owns no rendering information. It only supplies the same
    ``ClientState`` and timing inputs that the live GUI passes to ``GameFrame``.
    """

    name: str
    description: str
    state: ClientState
    default_size: tuple[int, int] = DEFAULT_SIZE
    interesting_frames: tuple[int, ...] = (0,)


WorkbenchScenario = ConnectWorkbenchScenario | LobbyWorkbenchScenario | GameWorkbenchScenario
ScenarioFactory = Callable[[], WorkbenchScenario]


def scenario_category(scenario: WorkbenchScenario) -> ScenarioCategory:
    match scenario:
        case ConnectWorkbenchScenario():
            return "connect"
        case LobbyWorkbenchScenario():
            return "lobby"
        case GameWorkbenchScenario():
            return "game"


def _connect_default() -> ConnectWorkbenchScenario:
    return ConnectWorkbenchScenario(
        name="connect-default",
        description="Unverändertes Verbindungsformular beim Programmstart.",
        connect_form=ConnectFormState(),
    )


def _connect_invalid_values() -> ConnectWorkbenchScenario:
    return ConnectWorkbenchScenario(
        name="connect-invalid-values",
        description="Ungültige Eingaben mit lokaler Validierungsfehlermeldung.",
        connect_form=ConnectFormState(
            host="",
            port="abc",
            display_name="",
            active_field="host",
            selected_field=None,
            auto_select_fields=(),
            error_message="Bitte gültige Werte für Server IP, Port und Anzeigename eingeben.",
        ),
    )


def _connect_error() -> ConnectWorkbenchScenario:
    return ConnectWorkbenchScenario(
        name="connect-error",
        description="Fehlgeschlagener Verbindungsversuch mit längerer Fehlermeldung.",
        connect_form=ConnectFormState(
            host="192.0.2.25",
            port="8765",
            display_name="Ada",
            active_field="host",
            selected_field=None,
            auto_select_fields=(),
            error_message=(
                "Verbindung fehlgeschlagen: Der Testserver antwortet nicht. "
                "Bitte Adresse, Port und Netzwerkverbindung prüfen."
            ),
            status_message="Bitte Werte prüfen und erneut verbinden.",
        ),
    )


def _connect_long_values() -> ConnectWorkbenchScenario:
    return ConnectWorkbenchScenario(
        name="connect-long-values",
        description="Layout-Grenzfall mit langen Server- und Anzeigenamen.",
        connect_form=ConnectFormState(
            host="row-taker-server.internes-schulnetz.example",
            port="65535",
            display_name="Ada-mit-einem-sehr-langen-Anzeigenamen",
            active_field="display_name",
            selected_field=None,
            auto_select_fields=(),
        ),
    )


def _lobby_view(
    occupants: tuple[tuple[str, str, ParticipantKind, str | None] | None, ...],
    *,
    extra_participants: tuple[tuple[str, str, ParticipantKind, str | None], ...] = (),
    endpoint: str = "127.0.0.1:8765",
) -> LobbyView:
    seats: list[LobbySeatView] = []
    participants: list[LobbyParticipantView] = []
    for seat_index, occupant in enumerate(occupants):
        if occupant is None:
            seats.append(
                LobbySeatView(
                    seat_index=seat_index,
                    occupant_client_id=None,
                    occupant_display_name=None,
                    occupant_kind=None,
                    occupant_endpoint=None,
                )
            )
            continue
        client_id, display_name, kind, occupant_endpoint = occupant
        seats.append(
            LobbySeatView(
                seat_index=seat_index,
                occupant_client_id=client_id,
                occupant_display_name=display_name,
                occupant_kind=kind,
                occupant_endpoint=occupant_endpoint,
            )
        )
        participants.append(
            LobbyParticipantView(
                client_id=client_id,
                display_name=display_name,
                participant_kind=kind,
                seat_index=seat_index,
                endpoint=occupant_endpoint,
            )
        )
    for client_id, display_name, kind, participant_endpoint in extra_participants:
        participants.append(
            LobbyParticipantView(
                client_id=client_id,
                display_name=display_name,
                participant_kind=kind,
                seat_index=None,
                endpoint=participant_endpoint,
            )
        )
    return LobbyView(
        seat_count=len(occupants),
        participants=tuple(participants),
        seats=tuple(seats),
        game_started=False,
        server_endpoint=endpoint,
    )


def _lobby_state(
    lobby: LobbyView,
    *,
    own_client_id: str = "client-ada",
) -> ClientState:
    state = reduce_server_message(initial_client_state(), IdentityAssigned(own_client_id))
    return reduce_server_message(state, LobbyStateUpdated(lobby=lobby))


def _lobby_empty() -> LobbyWorkbenchScenario:
    return LobbyWorkbenchScenario(
        name="lobby-empty",
        description="Leere Lobby direkt nach dem Verbinden.",
        state=_lobby_state(_lobby_view((None, None, None, None))),
    )


def _waiting_lobby_state() -> ClientState:
    return _lobby_state(
        _lobby_view(
            (
                ("client-ada", "Ada", ParticipantKind.HUMAN, "127.0.0.1:41001"),
                None,
                ("bot-clara", "Clara Bot", ParticipantKind.BOT, None),
                None,
            ),
            extra_participants=(("client-ben", "Ben", ParticipantKind.HUMAN, "192.0.2.12:52144"),),
        )
    )


def _lobby_waiting() -> LobbyWorkbenchScenario:
    return LobbyWorkbenchScenario(
        name="lobby-waiting",
        description="Gemischte Lobby mit Mensch, Bot, freien Plätzen und Zuschauer.",
        state=_waiting_lobby_state(),
    )


def _lobby_seat_selected() -> LobbyWorkbenchScenario:
    return LobbyWorkbenchScenario(
        name="lobby-seat-selected",
        description="Freier Sitz ist ausgewählt und die Sitzaktionen sind sichtbar.",
        state=enter_lobby_submenu(
            _waiting_lobby_state(),
            "seat_edit",
            selected_seat_index=1,
        ),
    )


def _lobby_bot_name_edit() -> LobbyWorkbenchScenario:
    state = enter_lobby_submenu(
        _waiting_lobby_state(),
        "bot_name",
        selected_seat_index=2,
    )
    state = with_navigation_updates(
        state,
        bot_name_text="Clara Bot mit langem Namen",
        bot_name_selected=True,
    )
    return LobbyWorkbenchScenario(
        name="lobby-bot-name-edit",
        description="Namenseingabe für einen vorhandenen lokalen Bot.",
        state=state,
    )


def _lobby_full() -> LobbyWorkbenchScenario:
    return LobbyWorkbenchScenario(
        name="lobby-full",
        description="Alle Sitzplätze sind mit Menschen und Bots belegt.",
        state=_lobby_state(
            _lobby_view(
                (
                    ("client-ada", "Ada", ParticipantKind.HUMAN, "127.0.0.1:41001"),
                    ("client-ben", "Ben", ParticipantKind.HUMAN, "192.0.2.12:52144"),
                    ("bot-clara", "Clara Bot", ParticipantKind.BOT, None),
                    ("bot-dorian", "Dorian Bot", ParticipantKind.BOT, None),
                )
            )
        ),
    )


def _lobby_long_names() -> LobbyWorkbenchScenario:
    return LobbyWorkbenchScenario(
        name="lobby-long-names",
        description="Lobby-Grenzfall mit langen Namen und Endpunktangaben.",
        state=_lobby_state(
            _lobby_view(
                (
                    (
                        "client-ada",
                        "Ada mit einem ungewöhnlich langen Namen",
                        ParticipantKind.HUMAN,
                        "2001:db8:1234:5678::100:41234",
                    ),
                    (
                        "client-ben",
                        "Benedikt-von-der-Testspielrunde",
                        ParticipantKind.HUMAN,
                        "lange-hostadresse.schulnetz.example:52144",
                    ),
                    (
                        "bot-clara",
                        "Clara Beispielspielerin Bot",
                        ParticipantKind.BOT,
                        None,
                    ),
                    None,
                ),
                extra_participants=(
                    (
                        "client-dorian",
                        "Dorian der Unerschrockene ohne Sitzplatz",
                        ParticipantKind.HUMAN,
                        "198.51.100.42:60000",
                    ),
                ),
                endpoint="row-taker-server.internes-schulnetz.example:8765",
            )
        ),
    )


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
    hand = tuple(Card(value) for value in (7, 17, 28, 39, 44, 53, 61, 70, 85, 101))

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
        message="Choose a row to take." if phase == Phase.CHOOSE_ROW else "Choose one card.",
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
    player_names: tuple[str, ...] = ("Ada", "Ben", "Clara", "Dorian"),
) -> ClientState:
    state = _base_state(rows=rows, player_names=player_names)
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


def _choose_card() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="choose-card",
        description="Ruhiger Spielzustand mit auswählbarer eigener Hand.",
        state=_base_state(),
    )


def _choose_row() -> GameWorkbenchScenario:
    base = _base_state()
    assert base.public_state is not None
    row_ids = tuple(row.row_id for row in base.public_state.rows)
    return GameWorkbenchScenario(
        name="choose-row",
        description="Eigener Spieler muss für die kleinste Karte eine Reihe wählen.",
        state=_base_state(
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
        state=_revealed_state(((0, 44), (1, 62), (2, 71), (3, 86))),
        interesting_frames=ANIMATION_FRAMES,
    )


def _card_placed() -> GameWorkbenchScenario:
    from row_taker.client.presentation_events import PresentationCardPlaced

    state = _advance_to_event(
        _revealed_state(((0, 44), (1, 62), (2, 71), (3, 86))),
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

    state = _with_choose_row_request(_revealed_state(((0, 7),)))
    state = _advance_to_event(state, PresentationRowChoiceRequired)
    return GameWorkbenchScenario(
        name="row-choice-required",
        description="Die kleinste Karte wartet auf eine externe Reihenwahl.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )


def _row_taken() -> GameWorkbenchScenario:
    from row_taker.client.presentation_events import PresentationRowTaken

    state = _with_choose_row_request(_revealed_state(((0, 7),)))
    assert state.public_state is not None
    state = reduce_server_message(
        state,
        RowChoiceCommitted(row_id=state.public_state.rows[1].row_id),
    )
    state = _advance_to_event(state, PresentationRowTaken)
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
    state = _advance_to_event(
        _revealed_state(((0, 53),), rows=rows),
        PresentationOverflowResolved,
    )
    return GameWorkbenchScenario(
        name="overflow-resolved",
        description="Eine sechste Karte löst einen Reihenüberlauf aus.",
        state=state,
        interesting_frames=ANIMATION_FRAMES,
    )


SIX_PLAYER_NAMES = ("Ada", "Ben", "Clara", "Dorian", "Emil", "Fatima")
SIX_PLAYER_PLAYS = ((0, 44), (1, 62), (2, 71), (3, 86), (4, 90), (5, 100))


def _five_opponents() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="five-opponents",
        description="Maximale Besetzung mit fünf kompakten Gegnerkacheln.",
        state=_base_state(player_names=SIX_PLAYER_NAMES),
    )


def _five_opponents_revealed() -> GameWorkbenchScenario:
    return GameWorkbenchScenario(
        name="five-opponents-revealed",
        description="Fünf überlappende Gegnerkarten und die eigene Karte sind aufgedeckt.",
        state=_revealed_state(SIX_PLAYER_PLAYS, player_names=SIX_PLAYER_NAMES),
        interesting_frames=ANIMATION_FRAMES,
    )


def _five_opponents_active() -> GameWorkbenchScenario:
    from row_taker.client.presentation_events import PresentationCardPlaced

    state = _advance_to_event(
        _revealed_state(SIX_PLAYER_PLAYS, player_names=SIX_PLAYER_NAMES),
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
        state=_revealed_state(((0, 44),)),
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
        state=_base_state(
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
    state = _base_state()
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
    state = _base_state(pending_action=PendingAction.NONE)
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
        state=_base_state(
            player_names=(
                "Ada mit einem ungewöhnlich langen Namen",
                "Benedikt-von-der-Testspielrunde",
                "Clara Beispielspielerin",
                "Dorian der Unerschrockene",
            )
        ),
    )


_SCENARIO_FACTORIES: dict[ScenarioCategory, dict[str, ScenarioFactory]] = {
    "connect": {
        "connect-default": _connect_default,
        "connect-invalid-values": _connect_invalid_values,
        "connect-error": _connect_error,
        "connect-long-values": _connect_long_values,
    },
    "lobby": {
        "lobby-empty": _lobby_empty,
        "lobby-waiting": _lobby_waiting,
        "lobby-seat-selected": _lobby_seat_selected,
        "lobby-bot-name-edit": _lobby_bot_name_edit,
        "lobby-full": _lobby_full,
        "lobby-long-names": _lobby_long_names,
    },
    "game": {
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
    },
}


def scenario_names(category: ScenarioCategory | None = None) -> tuple[str, ...]:
    if category is not None:
        return tuple(_SCENARIO_FACTORIES[category])
    return tuple(name for factories in _SCENARIO_FACTORIES.values() for name in factories)


def get_scenario(name: str) -> WorkbenchScenario:
    for factories in _SCENARIO_FACTORIES.values():
        factory = factories.get(name)
        if factory is not None:
            return factory()
    available = ", ".join(scenario_names())
    raise KeyError(f"unknown workbench scenario {name!r}; available: {available}")


def scenarios(category: ScenarioCategory | None = None) -> tuple[WorkbenchScenario, ...]:
    categories = (
        _SCENARIO_FACTORIES if category is None else {category: _SCENARIO_FACTORIES[category]}
    )
    return tuple(factory() for factories in categories.values() for factory in factories.values())
