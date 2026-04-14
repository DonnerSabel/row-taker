# Row-Taker – Design Decisions

## Purpose

This document records the intended target architecture of the Row-Taker project.
It is deliberately allowed to be ahead of the current code state.

Its purpose is not to describe every current implementation detail. Its purpose is
that a later reader can immediately see:

- which design ideas are already considered fixed
- which trade-offs were consciously chosen
- which future changes must respect these decisions

Where current code still differs from this document, the document wins as the
architectural direction.

---

## 1. Core architectural split

The project is split into four logically distinct areas.

### `engine/game`

This package contains the game rules and game-state structures.

Typical responsibilities:
- cards, rows, scoring
- game-state transitions
- round and trick progression
- trick resolution
- game-related state structures such as `GameState`, `PublicState`, and `PlayerState`

This layer must stay domain-pure. It must not depend on networking, server process
management, CLI concerns, or GUI concerns.

### `engine/lobby`

This package contains the lobby domain model.

Typical responsibilities:
- available seats
- mapping `seat -> client_id`
- seat assignment, clearing, and moving
- simple start preconditions

The lobby is intentionally metadata-light. It does not know display names,
participant kinds, or transport details.

### `server/*`

This area contains server-bound orchestration and participant management.

Typical responsibilities:
- participant management
- registry
- server-side attachment / reachability of participants
- building protocol-facing views
- transition from lobby to running match
- mappings such as `client_id <-> player_id`

The server is not a second rule engine. It uses the shared engine.

### `protocol/*`

This area contains the transport-facing message types, codec, and transport.

Its role is to define minimal synchronization messages between server and clients,
without forcing the internal domain model to mirror transport messages exactly.

---

## 2. Shared engine basis

The engine is the shared foundation for all game-state structures used by both
clients and the server.

Consequences:
- the server does not own a separate game-rule model
- clients and server are expected to rely on the same game-domain concepts
- client-side interpretation and rendering should build on the shared engine model
  rather than on server-private orchestration details

This applies in particular to:
- `GameState`
- `PublicState`
- `PlayerState`
- trick-resolution structures
- the local reconstruction of the visible game flow

The engine is therefore the real semantic heart of the project.

---

## 3. Protocol reconstruction principle

The client/server protocol is designed so that the real game flow of *6 nimmt!*
can be reconstructed fully.

At the same time, it is intentionally minimal.

Consequences:
- the protocol should transmit only the information needed for synchronization and
  player interaction
- additional interpretation should, where appropriate, be reconstructed locally with
  the help of the shared engine
- the server should not transmit redundant derived state merely for presentation
  convenience if the same meaning can be reconstructed from protocol data plus shared
  engine logic

This means the clients are not supposed to be dumb terminals. They are expected to
use the shared engine.

A short formulation of the design is:

**Protocol: as small as possible. Engine: as rich as necessary.**

---

## 4. Process separation

Each client and the server run in their own process.

Consequences:
- the server is never embedded inside a client process
- every CLI client, GUI client, and bot is a separate process
- for a game with `n` players there are always `n + 1` processes in total: one
  server process and `n` participant processes

This process-level separation is intentional. It keeps all participants technically
symmetric and avoids special host-client behaviour.

---

## 5. Participants, identity, and display

### Core unification

Bots and humans are both regular participants identified by a `client_id`.

Consequences:
- a bot is not a special-case lobby concept
- a human is not more fundamental than a bot
- differences between participants are modelled as metadata, not as separate lobby
  entities

### Stable identity

The only stable identity of a participant is `client_id`.

### Display name

`display_name` is mutable presentation data.

Consequences:
- internal references must use `client_id`
- `client_id` and `display_name` must never be conflated
- renaming a participant must not affect identity or seat ownership

### Participant model

Participants are described server-side by a shared participant model.

A participant has at least:
- `client_id`
- `display_name`
- `kind`
- `location`

Current distinctions include:
- `HUMAN`
- `BOT`

and
- `LOCAL`
- `REMOTE`

This belongs to the server-side participant model, not to the lobby.

---

## 6. Registry and lobby

### Registry

The registry is the central place that manages participants.

It contains:
- participant metadata
- server-side attachment / reachability of a participant
- the information needed by the server to address that participant

The registry does not know seats.

### Lobby

The lobby is intentionally small.

It knows only:
- available seats
- mapping `Seat -> client_id`
- whether a seat is free or occupied
- whether a game has already started

It does not store:
- `display_name`
- participant kind
- bot-specific metadata
- network metadata
- other participant metadata

The lobby therefore describes only **which `client_id` sits where**, not **what kind
of participant it is**.

### Current lobby structure

`LobbyState` is still a current target concept, but only in deliberately reduced
form. It is a minimal internal model for lobby domain logic.

### Deprecated intermediate models

The following older intermediate models are not target concepts anymore:
- `ConnectedClient`
- `SeatConfig`

These may still exist in older code or documents, but they are not the intended
architectural direction.

### Lobby view

Clients still need a richer lobby representation.

Therefore:

**The lobby view is derived server-side from lobby + registry.**

The internal lobby stays small. Richer presentation data is derived when needed.

---

## 7. Minimal game protocol

For the actual gameplay, the protocol should stay minimal but semantically complete.

The required synchronization points are:
- common game / round start with the same initial data on all sides
- full reveal of all chosen cards of the trick
- row choice when required
- administrative messages such as game end, abort, disconnect, or player removed

These are the core gameplay synchronization points.

### Game protocol philosophy

The server should not broadcast:
- public score updates after every micro-step
- public state snapshots after every micro-step
- row contents after every micro-step
- presentation-oriented explanations that can be reconstructed locally

Instead, each process should reconstruct the visible trick progression locally by
using the shared engine.

### Target client-to-server messages

For the actual game protocol, the intended target is:
- `SubmitCard(card_id)`
- `SubmitRowChoice(row_id)`

The acting player must be derived from the connection / session on the server.
Clients should not claim a `player_id` inside these game messages.

### Target server-to-client messages

For the actual game protocol, the intended target is a small set of messages such as:
- game / round start data
- `CardsRevealed(plays=[...])`
- row-choice related synchronization
- administrative game-end / abort / disconnect messages

The exact type names may still change. The architectural idea is fixed.

---

## 8. `CardsRevealed` semantics

The reveal message for a trick contains the complete set of chosen cards.

Important semantic decision:

**`CardsRevealed.plays` is conceptually unordered.**

The JSON representation may use a list, but this list order carries no gameplay
meaning.

Consequences:
- clients must not interpret list position as reveal order
- clients must not interpret transport arrival order as gameplay order
- the local engine determines the resolution order from the game rules

Typical structure:

```json
{
  "type": "cards_revealed",
  "plays": [
    {"player_id": "p1", "card_id": 17},
    {"player_id": "p2", "card_id": 42},
    {"player_id": "p3", "card_id": 8}
  ]
}
```

The number of list entries naturally depends on the player count. This is not a
problem and is the intended modelling choice.

---

## 9. Transport ordering and client-side processing

The transport layer uses TCP with line-based message framing.

This matters for architecture in the following way:
- bytes are received in the order in which they were sent on one connection
- message A cannot overtake message B on the same connection
- a later debug message therefore also arrives after earlier gameplay messages on
  that same connection

This does **not** mean that the GUI should directly treat arrival as presentation.

Every client must carefully separate:
1. **receive** a message
2. **apply** it to the local semantic model
3. **render** or animate the consequences

This separation is essential.

A client may still be rendering or animating earlier visible consequences while later
messages have already been received. That is fine, as long as the semantic ordering is
kept intact.

The architectural problem is therefore not "message overtaking" but the clean
separation of:
- network inbox
- semantic application
- presentation timing

---

## 10. Engine-side local resolution

After the protocol synchronization points, the further visible trick progression
should be reconstructed locally in every client and in the server with the help of
the shared engine.

This includes, for example:
- recognizing that a card can be placed normally
- recognizing row overflow
- recognizing that the smallest card must choose a row
- recognizing which player must choose
- recognizing which row is taken
- recognizing taken cards and resulting bullheads

The server should not narrate each of these micro-steps through gameplay messages.
The engine should make them available locally.

---

## 11. Resolver / Stepper as target trick-resolution model

The intended target model for trick resolution is a local **resolver / stepper**.

This is not a network protocol object. It is a local engine mechanism.

### Why a resolver / stepper

The trick resolution of *6 nimmt!* is naturally stepwise:
- cards become relevant as a complete revealed set
- the engine can determine the next semantic step
- at certain points an external choice may be required
- after that choice, the resolution continues

A resolver / stepper models this directly.

### Conceptual shape

The intended shape is roughly:
- create a resolver from the current state plus `CardsRevealed`
- repeatedly ask the resolver for the next semantic step
- if a row choice is required, the resolver pauses with a dedicated step
- after `SubmitRowChoice(row_id)` has been applied, the resolver continues
- continue until the trick is fully resolved

### Important clarification

The resolver / stepper is **not** a single linked list.

It is better understood as:
- a local stateful resolution object
- with a notion of "next semantic step"
- and with possible pause points for external input

The key benefit is not list-like linking. The key benefit is that the engine can
always answer:

**What is the next semantic step of the trick?**

### Why this is preferred over callbacks / hooks

Callbacks or GUI hooks inside the engine are not the target.

The GUI should not be called by the engine.
The GUI should observe engine-produced semantic steps.

This keeps:
- the engine testable
- the engine independent from UI code
- the CLI and GUI symmetric
- the local semantic flow explicit

---

## 12. Semantic steps for GUI and CLI

The GUI and CLI should consume semantic steps produced locally by the engine.

The exact class names are still open, but the kinds of local semantic information
that matter are already clear.

Examples include:
- a card is placed normally
- a row is taken because the card is too small
- a row overflows and is taken
- a row choice is required
- a particular player is the chooser
- the trick is finished

The local UI may animate these steps at its own speed.

The important rule is:

**No additional game logic should be reinvented in the UI.**

---

## 13. Event-list vs resolver / stepper

Two local engine-facing shapes were considered seriously:
- a precomputed event list
- a resolver / stepper

### Event-list strengths

A precomputed event list is easy to play back in a GUI loop and easy to test.
It is also naturally useful as a debug trace.

### Event-list weakness

As soon as external input is required in the middle of a trick, the event list tends
to split into partial batches. This is workable, but less natural.

### Resolver / stepper strengths

A resolver / stepper matches the true nature of the trick resolution better:
- it is stepwise
- it has natural pause points
- it can continue after external choices
- it gives both CLI and GUI the same next-step view

### Decision

The target architecture prefers the **resolver / stepper** as the real local
resolution mechanism.

A UI-friendly event queue may still exist as a local consumption pattern, but it is
not the primary semantic model.

---

## 14. Debugging philosophy

The project explicitly distinguishes between:
- the minimal gameplay protocol
- optional rich debugging support

This separation is intentional.

### Gameplay protocol

The gameplay protocol should remain minimal and semantically complete.
It should not be polluted by half-debugging redundancy.

### Debugging support

Debugging may intentionally be much richer.

Possible debugging data includes:
- the full authoritative `GameState`
- public and player projections
- the current server-side phase / pending action
- a semantic trace of resolution steps
- internal mappings that are useful for diagnosis

This is allowed exactly because it is debugging, not gameplay.

### Important rule

Debugging information is an addition, not a replacement for a correct gameplay
protocol.

---

## 15. Debugging snapshots and sequencing

Because clients may animate slowly, it must be considered from the start that a
client can already have received several later messages while still visually playing
older effects.

Therefore a rich debugging message should not be treated as a blind visual reset.
It should be understandable in relation to the semantic application history.

A suitable debugging design may therefore include metadata such as:
- a revision number
- a sequence number
- a trick number and step number
- or another explicit "applied through here" marker

The exact scheme is still open.
The architectural decision is only that optional debugging output must be designed
with semantic sequencing in mind.

---

## 16. Current code versus target direction

This document is intentionally allowed to be ahead of the current code.

Examples of code that may still lag behind this design include:
- game messages that still redundantly carry `player_id`
- older hub-centric message naming
- trick resolution that is still too delta-based and not yet semantic enough
- documents that still describe the older hub language too strongly

These gaps are expected during the transition.
They should be resolved in the direction documented here.

---

## 17. Practical guidance for later work

When changing the project later, these questions should be asked first:

1. Does this keep the engine as the semantic heart of the game?
2. Does this keep the gameplay protocol minimal but semantically complete?
3. Does this avoid pushing gameplay logic into GUI or CLI code?
4. Does this respect the separation of receive / apply / render?
5. Does this support the resolver / stepper direction for local trick resolution?
6. Does this keep debugging support clearly separate from gameplay protocol data?

If the answer to one of these questions is no, the change is likely moving in the
wrong direction.


## Presentation-Schicht als GUI-Andockfläche

Zwischen lokaler Spielauflösung und konkreter Oberfläche liegt eine eigene, GUI-neutrale Presentation-Schicht.

Leitidee

- Die Engine und die client-seitige Auflösung kennen nur fachliche Daten.
- Die Presentation-Schicht übersetzt diese fachlichen Daten in strukturierte Presentation-Events.
- CLI und GUI rendern dieselben Presentation-Events jeweils auf ihre eigene Weise.
- Auf dieser Ebene gibt es **keine** GUI-Objekte und keine pygame-Abhängigkeiten.

Typische Event-Typen

- `PresentationCardsRevealed`
- `PresentationCardPlaced`
- `PresentationRowChoiceRequired`
- `PresentationRowChosen`
- `PresentationRowTaken`
- `PresentationOverflowResolved`
- `PresentationTrickFinished`

Wichtige Regel

`card_value` ist die fachliche Karten-ID. Die GUI hält ihr eigenes Mapping von `card_value` auf ihr konkretes GUI-Kartenobjekt.

Beispielidee in Pseudocode

```python
cards_by_value: dict[int, GuiCard]

for event in presentation_events:
    match event:
        case PresentationCardsRevealed(plays=plays):
            for play in plays:
                cards_by_value[play.card_value].flip_face_up()
        case PresentationCardPlaced(card_value=value, row_id=row_id):
            gui_card = cards_by_value[value]
            table.animate_card_to_row(gui_card, row_id)
        case PresentationRowChoiceRequired(player_id=player_id):
            overlays.show_row_choice(player_id)
```

### Session end and shutdown

A session-ending event is represented explicitly by `SessionEnded`.

Consequences:
- when one participant ends the session, the server informs all remaining clients
- all remaining clients terminate their local session flow on `SessionEnded`
- this includes local bot processes as well as human clients
- the server then shuts down automatically once the session has ended and no
  connected participants or running bot processes remain

This is intentionally modelled as a session-ended policy, not as a special rule
based on the presence or absence of human participants.

## 9. Presentation layer on the client

Clients use a GUI-neutral presentation layer as the direct bridge between local
rule reconstruction and visible rendering.

Consequences:
- local resolver / stepper output is translated into `PresentationEvent` objects
- CLI and GUI both consume this layer
- this layer must not contain GUI-specific objects
- cards are referenced by their fachliche identity, typically `card_value`
- a GUI owns and manages its own visual card objects

A short formulation is:

**Engine produces semantics. Presentation describes visible meaning. GUI owns visuals.**

## 10. Logging and diagnostics

The project uses structured Python logging instead of temporary ad-hoc `print`
debugging.

Consequences:
- server, CLI clients, and bot processes should all be loggable independently
- log verbosity is controlled via log levels such as `INFO` and `DEBUG`
- file logging is a first-class debugging workflow, especially for multi-process
  runs
- local bot processes inherit the server log level and derive their own log file
  path from the server log path when one is configured

This logging infrastructure is not just convenience. It is part of the intended
diagnostics design for later debugging, including future richer debug messages or
snapshots.


## 10. Canonical client pipeline

The canonical client pipeline is centered around `GameClientCore`.

Consequences:
- frontends feed server messages into `GameClientCore.on_server_message(...)`
- frontends feed user actions into `GameClientCore.on_ui_action(...)`
- the core owns inbox, deferring, revision tracking, and the presentation queue
- `CliApp` is the CLI host layer around the core
- `state_machine.py` is no longer a productive abstraction

### Core result objects

`GameClientCore` returns a `CoreUpdate` object with at least:
- `state`
- `applied_server_messages`
- `outbound_messages`
- `local_messages`

### Shared core for human clients and bots

Target model:
- human client = `GameClientCore` + frontend
- bot = `GameClientCore` + decision layer
