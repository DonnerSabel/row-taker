# GameClientCore API

This document is intentionally written for later GUI work and for students.

## Purpose

`GameClientCore` is the canonical client pipeline.

A frontend should not implement game-flow logic itself. Instead, it should:

1. feed server messages into the core
2. feed user actions into the core
3. render the returned state
4. send the returned outbound messages to the server
5. optionally react to the returned effects

## The two main methods

```python
update = core.on_server_message(message)
update = core.on_ui_action(action)
```

Both methods return a `CoreUpdate`.

## CoreUpdate

A `CoreUpdate` contains:

- `state`: the new `ClientCoreState`
- `applied_server_messages`: which queued server messages were really applied
- `outbound_messages`: messages that the frontend must send to the server
- `local_messages`: local validation messages for the frontend
- `effects`: small frontend-visible transition hints

The frontend should treat `state` as the new truth.

The additional fields exist so that the frontend does not have to infer every
transition by manually diffing old and new states.

## Minimal frontend pattern

```python
update = core.on_ui_action(UiActionChooseCard(card_value))

for message in update.outbound_messages:
    transport.send(message)

render(update.state)
```

And for incoming network traffic:

```python
update = core.on_server_message(server_message)

for message in update.outbound_messages:
    transport.send(message)

render(update.state)
```

## Example 1: choosing a card in a GUI

```python
def on_card_clicked(card_value: int) -> None:
    update = core.on_ui_action(UiActionChooseCard(card_value))

    if update.local_messages:
        show_error(update.local_messages[-1])

    for message in update.outbound_messages:
        transport.send(message)

    render_from_core_state(update.state)
```

## Example 2: receiving CardsRevealed

```python
def on_server_message(message) -> None:
    update = core.on_server_message(message)

    render_from_core_state(update.state)

    for effect in update.effects:
        handle_effect(effect)
```

If the message is `CardsRevealed`, the core may:

- queue local presentation events
- keep later messages deferred internally
- expose those queued presentation steps through the returned state and effects

The frontend should not re-implement this logic.

## Example 3: bot usage

```python
update = core.on_server_message(message)
state = update.state

if state.pending_action == PendingAction.CHOOSE_CARD:
    action = choose_bot_card(state.player_state)
    reply = core.on_ui_action(action)
    for outbound in reply.outbound_messages:
        transport.send(outbound)
```

This is why the project treats `GameClientCore` as a shared networked-client layer for
human clients and bots.

## Boundaries

### Engine
The engine is the authority over the game rules.

### GameClientCore
The core is the authority over the client-side processing of:

- server messages
- user actions
- inbox and deferring
- presentation queue
- revision tracking

### Frontend
The frontend is responsible for:

- text input or mouse/keyboard input
- rendering
- sending returned outbound messages
- optionally reacting to effects

## Rule of thumb

If a GUI has to ask:
What should I do after this click or this incoming server message?

then the answer should usually come from `GameClientCore`, not from GUI-specific
business logic.
