from __future__ import annotations

from row_taker.gui.connect_form_state import ConnectFormState
from row_taker.gui_workbench.scenario_types import (
    ConnectWorkbenchScenario,
    ScenarioFactory,
)


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

CONNECT_SCENARIO_FACTORIES: dict[str, ScenarioFactory] = {
    "connect-default": _connect_default,
    "connect-invalid-values": _connect_invalid_values,
    "connect-error": _connect_error,
    "connect-long-values": _connect_long_values,
}
