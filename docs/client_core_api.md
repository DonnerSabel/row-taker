# GameClientCore API

Diese Datei beschreibt den gemeinsam von CLI, GUI und Bots verwendeten Client-Core.

## Idee

`GameClientCore` ist der fachliche Client-Kern.

Ein Frontend soll nicht selbst ueberlegen, wie Servernachrichten, lokale Praesentation,
Revisionsstand und Outbound-Nachrichten zusammenspielen. Stattdessen soll es:

1. Servernachrichten an den Core geben
2. UI-Aktionen an den Core geben
3. den neuen Zustand rendern
4. die vom Core gelieferten Outbound-Nachrichten senden

## Die zwei wichtigsten Methoden

```python
update = core.on_server_message(message)
update = core.on_ui_action(action)
```

Beide liefern ein `CoreUpdate`.

## CoreUpdate

`CoreUpdate` enthaelt:

- `state`: der neue Client-Zustand
- `applied_server_messages`: welche Nachrichten aus der Inbox wirklich angewendet wurden
- `outbound_messages`: diese Nachrichten muss das Frontend an den Server senden
- `local_messages`: lokale Fehlermeldungen fuer das Frontend

## Beispiel: Karte in einer GUI anklicken

```python
def on_card_clicked(card_value: int) -> None:
    update = core.on_ui_action(ClientActionChooseCard(card_value))

    if update.local_messages:
        show_error(update.local_messages[-1])

    for message in update.outbound_messages:
        transport.send(message)

    render_from_state(update.state)
```

## Beispiel: Servernachricht empfangen

```python
def on_server_message(message) -> None:
    update = core.on_server_message(message)

    for outbound in update.outbound_messages:
        transport.send(outbound)

    render_from_state(update.state)
```

## Beispiel: Bot

```python
update = core.on_server_message(message)
state = update.state

if state.client_mode == ClientMode.GAME and state.pending_action == PendingAction.CHOOSE_CARD:
    assert state.player_state is not None
    action = ClientActionChooseCard(choose_bot_card(state.player_state))
    reply = core.on_ui_action(action)
    for outbound in reply.outbound_messages:
        transport.send(outbound)
```

## Grenzen

### Engine
Die Engine ist fuer Spielregeln und fachliche Wahrheit zustaendig.

### GameClientCore
Der Core ist fuer die clientseitige Verarbeitung von
- Servernachrichten
- UI-Aktionen
- Inbox und Deferring
- lokaler Praesentation
zuständig.

### Frontend
Das Frontend ist fuer Rendering, Eingabe und das Versenden der Outbound-Nachrichten zustaendig.


## Frontend state axes

Frontends sollen fachliche Entscheidungen primaer an diesen Achsen ausrichten:

- `state.client_mode`
- `state.pending_action`
- `state.navigation_state`

`LobbyScreen` und `GameScreen` sind nur noch abgeleitete View-Objekte. Sie duerfen
beim Rendern hilfreich sein, sollen aber nicht mehr die fuehrende Wahrheit fuer
Prompt-Bestimmung oder Texteingabe sein.


## Zustandsübergänge

`ClientState` wird nicht über generische `**changes`-Hilfsfunktionen verändert.
Stattdessen stellt `row_taker.client.state` konkret typisierte Übergänge bereit, zum Beispiel:

- `assign_identity(...)`
- `prepare_game_start(...)`
- `request_card_choice(...)`
- `request_row_choice(...)`
- `set_flash_message(...)` und `clear_flash_message(...)`
- `request_exit(...)`
- `set_bot_name_editor(...)`

Dadurch sind erlaubte Felder und Werttypen an der Funktionssignatur sichtbar. Frontends
verwenden dieselben Transitionen, ohne selbst verschachtelte `dataclasses.replace()`-Aufrufe
für Core-, Navigation- oder Feedback-Zustände zusammenzustellen.

Die CLI leitet Eingabe, Prompt und Rendering direkt aus `ClientState` ab. Die Tests sind
entlang der Architekturgrenzen getrennt in Core-, Frontend- und Render-Tests.


## Reducer und fachliche Transitionen

Der Reducer ist bewusst nur ein expliziter Dispatcher. Er enthält keine
Validierungs-, Lobby- oder Präsentationslogik:

```text
core_reducer.py
    ├── Servernachricht → server_transitions.py
    └── ClientAction    → action_transitions.py

presentation_queue.py
    verwaltet sichtbare und noch ausstehende PresentationStep-Objekte
```

`server_transitions.py` verarbeitet die fachliche Bedeutung einzelner
Servernachrichten. `action_transitions.py` validiert lokale Aktionen und liefert
einen `ActionResult` mit neuem Zustand, optionaler Outbound-Nachricht und
optionaler lokaler Meldung. Die zentrale `match`-Anweisung bleibt dadurch als
vollständiges Inhaltsverzeichnis aller unterstützten Eingaben lesbar, ohne eine
Handler-Registry oder Factory-Klassen einzuführen.

## Fehler bei lokalen Aktionen

`action_transitions.py` unterscheidet erwartete Validierungsfehler von
Programmierfehlern:

- `ValueError` aus der fachlichen Karten- oder Reihenvalidierung wird als
  `CoreUpdate.local_messages` an das Frontend zurückgegeben.
- Andere Ausnahmen werden nicht in eine gewöhnliche Benutzermeldung
  umgewandelt. Sie müssen an einer äußeren Infrastrukturgrenze geloggt und
  behandelt werden.

Damit kann eine ungültige Auswahl die Sitzung nicht beschädigen, während ein
Programmierfehler weiterhin sichtbar bleibt und nicht wie eine falsche
Benutzereingabe aussieht.
