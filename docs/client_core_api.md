# GameClientCore API

Diese Datei ist bewusst fuer den spaeteren GUI-Bau und fuer Schueler geschrieben.

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
    update = core.on_ui_action(UiActionChooseCard(card_value))

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

if isinstance(state.screen, GameScreen) and state.screen.kind == "choose_card":
    action = UiActionChooseCard(choose_bot_card(state.screen.player_state))
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
