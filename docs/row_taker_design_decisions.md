# Row-Taker – Design Decisions

## Purpose

This document records the current architectural and modelling decisions for the Row-Taker project. It explains how the system is split, which concepts are intentionally kept separate, and which direction should guide further development.

It is not a full API reference. Its purpose is to document the main design decisions and their consequences.

---

## 1. Architectural split

The project is split into three logically distinct areas.

### `engine/game`

This package contains the game rules and game state.

Typical responsibilities:
- cards, rows, score calculation
- game state and trick resolution
- round progression
- game-related state structures such as `PlayerState` or `PublicState`

This layer should stay as domain-pure as possible and should not depend on networking, server process details, or CLI concerns.

### `engine/lobby`

This package contains the lobby domain model.

Typical responsibilities:
- available seats
- mapping `seat -> client_id`
- assigning, clearing, and moving seats
- simple start preconditions

The lobby is intentionally metadata-light. It does not know participant names, participant kinds, or transport details.

### `server/*`

This area contains server-bound orchestration and participant management.

Typical responsibilities:
- participant management
- registry
- server-side reachability / attachment of participants
- building protocol views
- transition from lobby to running match
- mappings such as `client_id <-> player_id`

This layer is server-specific and is not part of the pure game or lobby domain.

### `protocol/*`

This area contains the message types and codec used between server and clients.

Its role is to define transport-facing structures without forcing the internal domain model to mirror them exactly.

---

## 2. Core unification: bots and humans are regular participants

The central unifying decision is:

**Bots and humans are both regular participants identified by a `client_id`.**

Consequences:
- a bot is not a special-case lobby concept
- a human is not more fundamental than a bot
- differences between participants are modelled as metadata, not as separate lobby entities

This keeps the model robust for:
- local server-side participants
- TCP-connected participants
- human participants
- bots
- future replacement of disconnected participants

---

## 3. Identity vs display

### Stable identity

The only stable identity of a participant is `client_id`.

### Display name

`display_name` is only mutable presentation data.

Consequences:
- internal references must use `client_id`
- `client_id` and `display_name` must never be conflated
- renaming a participant must not affect identity or seat ownership

---

## 4. Participant model

Participants are described server-side by a shared participant model.

A participant has at least:
- `client_id`
- `display_name`
- `kind`
- `location`

Current distinctions:
- `HUMAN`
- `BOT`

and
- `LOCAL`
- `REMOTE`

This belongs to the server-side participant model, not to the lobby.

---

## 5. Registry

The registry is the central place that manages all participants.

It contains:
- participant metadata
- the server-side attachment / reachability of a participant
- the information needed by the server to address that participant

The registry may include:
- human clients
- local participants
- remote participants
- bots

**The registry does not know seats.**

It is not a lobby model.

---

## 6. Lobby model

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

The lobby therefore describes only **which `client_id` sits where**, not **what kind of participant it is**.

---

## 7. Current internal lobby structure

The current internal lobby structure is `LobbyState`.

`LobbyState` is still current, but only in deliberately reduced form. It contains only the data required for lobby domain logic.

Typical fields include:
- `seat_count`
- `seats`
- `game_started`

A seat contains only:
- `seat_index`
- `occupant_client_id`

`LobbyState` is an internal minimal model. It is not the same thing as the lobby representation sent to clients.

---

## 8. Deprecated intermediate models

The following older intermediate models are no longer part of the target architecture.

### `ConnectedClient`

Not current anymore.

Participant metadata and seat assignment are now separated more cleanly into:
- participant / registry
- `LobbyState`
- protocol-facing lobby view

### `SeatConfig`

Not current anymore.

The lobby no longer provides participant names or participant kinds for match startup. Instead:
- the lobby only provides `seat -> client_id`
- the transition into a running match uses a dedicated mapping model

These older types should not be treated as architectural target concepts.

---

## 9. Lobby view

Although the internal lobby is metadata-light, clients still need a richer representation.

Therefore:

**The lobby view is derived server-side from lobby + registry.**

The server combines:
- seat occupancy from the internal lobby model
- participant metadata from the registry

and produces protocol-facing messages, for example with:
- seat index
- `occupant_client_id`
- `occupant_display_name`
- participant kind
- other presentation-oriented fields

Important:
- the richer view is allowed
- it is presentation data, not internal lobby state

---

## 10. Responsibilities of server and clients

### Server

The server:
- owns the internal truth
- manages registry and lobby
- derives protocol messages from internal state
- manages participant reachability / attachment
- starts matches and maintains runtime mappings

### Clients

Clients:
- receive protocol messages
- render those messages
- send input back
- do not reconstruct internal server models

Clients do not build their own domain-level lobby view. They only render the view already produced by the server.

---

## 11. Transition from lobby to running match

The mapping between lobby participants and actual players exists **only once a match starts**.

Before match start there are only:
- seats
- occupied `client_id`s

At match start this becomes:
- `player_id -> client_id`
- `client_id -> player_id`

This mapping belongs to the running match, not to:
- the registry
- the lobby

This preserves the distinction:
- lobby = seating before the game
- match = actual player mapping during the game

---

## 12. `MatchParticipants` as explicit transition model

The transition from lobby to match uses an explicit mapping structure.

It contains in particular:
- ordered seated `client_id`s
- `player_to_client_id`
- `client_to_player_id`

Order is derived from occupied seats in seat order.

This makes the design explicit:

**Player IDs are not general participant properties. They arise only when a match begins.**

---

## 13. Bot logic

Bots are regular participants at the domain level.

Their creation and technical attachment are server responsibilities.

Consequences:
- a bot is first created server-side as a participant
- afterwards its `client_id` is assigned to a seat
- the lobby treats it like any other participant

Bot-specific decisions therefore belong:
- in the server layer
- in registry / reachability logic

They do not belong in the lobby domain model.

---

## 14. Internal model vs protocol model

Internal models and protocol messages are intentionally kept separate.

### Internal models

Live in:
- `engine/game`
- `engine/lobby`
- `server/*`

### Protocol models

Live in:
- `protocol/messages.py`
- `protocol/codec.py`

Important:
- protocol types may contain richer view data
- internal domain models should not be inflated just to match protocol messages
- the codec works with protocol types, not with internal lobby dataclasses

---

## 15. CLI and other clients

The CLI is a client of the server and should work only with protocol messages.

This means:
- no direct dependency on internal lobby structures
- no imports of deprecated intermediate models such as `ConnectedClient` or `SeatConfig`
- rendering is based on messages such as:
  - `LobbyStateUpdated`
  - `StateUpdated`
  - `ChooseCardRequested`
  - `ChooseRowRequested`
  - `TrickResolved`

If internal server or lobby types appear in the CLI, that is a design warning sign.

---

## 16. Future network and bot flexibility

The architecture is intentionally designed to allow multiple technical attachment styles.

This includes:
- local server-side participants
- remote TCP-connected participants
- human participants
- bots

The model based on regular participants and `client_id` keeps these extensions open without changing the core domain model.

---

## 17. Important separations

The following concepts should not be mixed:
- `client_id` and `display_name`
- registry and lobby
- participant identity and seat assignment
- lobby state and lobby view
- participant identity and in-match player position
- pure domain logic and server-bound orchestration

These separations are intentional and should guide future work.

---

## 18. Practical consequences for future changes

The following rules should guide further development:

1. New participant metadata belongs in the server-side participant model or registry, not in the lobby.
2. Presentation-only data should be added as a view or protocol concept, not as internal lobby state.
3. Player IDs and player positions arise only when a match starts.
4. Bots must not be modelled via special fields in the lobby model.
5. Clients should not reconstruct internal domain models.
6. Deprecated intermediate models such as `ConnectedClient` and `SeatConfig` should not be reintroduced.

---

## 19. Architecture guideline

The current architecture can be summarized as follows:

**`engine/*` contains pure, transport-light domain logic.**  
**`server/*` contains server-bound participant management and orchestration.**  
**`protocol/*` defines the messages exchanged between server and clients.**
