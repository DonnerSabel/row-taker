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


## Stand nach Umbauzug 2

Die CLI leitet nun nicht nur Eingabe und Prompt, sondern auch das Haupt-Rendering primär aus `ClientState` ab. `cli/screens.py` bleibt als abgeleitete View-Projektion erhalten, ist aber nicht mehr die führende Produktionslogik für das Rendering.

Die Tests sind entlang der Architekturgrenzen getrennt in Core-, Frontend- und Render-Tests.
