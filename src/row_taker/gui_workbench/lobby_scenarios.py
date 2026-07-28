from __future__ import annotations

from row_taker.client.state import ClientState, enter_lobby_submenu, set_bot_name_editor
from row_taker.gui_workbench.scenario_builders import build_lobby_state, build_lobby_view
from row_taker.gui_workbench.scenario_types import LobbyWorkbenchScenario, ScenarioFactory
from row_taker.participants import ParticipantKind


def _lobby_empty() -> LobbyWorkbenchScenario:
    return LobbyWorkbenchScenario(
        name="lobby-empty",
        description="Leere Lobby direkt nach dem Verbinden.",
        state=build_lobby_state(build_lobby_view((None, None, None, None))),
    )


def _waitingbuild_lobby_state() -> ClientState:
    return build_lobby_state(
        build_lobby_view(
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
        state=_waitingbuild_lobby_state(),
    )


def _lobby_seat_selected() -> LobbyWorkbenchScenario:
    return LobbyWorkbenchScenario(
        name="lobby-seat-selected",
        description="Freier Sitz ist ausgewählt und die Sitzaktionen sind sichtbar.",
        state=enter_lobby_submenu(
            _waitingbuild_lobby_state(),
            "seat_edit",
            selected_seat_index=1,
        ),
    )


def _lobby_bot_name_edit() -> LobbyWorkbenchScenario:
    state = enter_lobby_submenu(
        _waitingbuild_lobby_state(),
        "bot_name",
        selected_seat_index=2,
    )
    state = set_bot_name_editor(
        state,
        text="Clara Bot mit langem Namen",
        selected=True,
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
        state=build_lobby_state(
            build_lobby_view(
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
        state=build_lobby_state(
            build_lobby_view(
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


LOBBY_SCENARIO_FACTORIES: dict[str, ScenarioFactory] = {
    "lobby-empty": _lobby_empty,
    "lobby-waiting": _lobby_waiting,
    "lobby-seat-selected": _lobby_seat_selected,
    "lobby-bot-name-edit": _lobby_bot_name_edit,
    "lobby-full": _lobby_full,
    "lobby-long-names": _lobby_long_names,
}
