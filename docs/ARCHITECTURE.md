# Architektur

## Leitidee

Das Projekt trennt bewusst drei Ebenen:

- **Engine** – kennt die fachlichen Regeln und Zustandsübergänge
- **Hub** – orchestriert ein laufendes Spiel über Messages
- **Clients** – reagieren auf Hub-Messages und senden Antworten zurück

Der Hub ist dabei **nicht** der zweite Regelkern. Er benutzt die Engine.

## Zentrale Zustände

### `GameState`
Der autoritative interne Spielzustand des Hubs.

Enthält unter anderem:
- Spieler mit echten Händen und Punkteständen
- Reihen auf dem Tisch
- Deck
- Phasen- und Auflösungskontext

`GameState` bleibt im Hub und wird nicht als Nachricht verteilt.

### `PublicState`
Der fachliche öffentliche Zustand des Spiels.

Er enthält genau die Informationen, die alle Clients sehen dürfen, zum Beispiel:
- öffentliche Spielerdaten (`name`, `score`, `hand_count`)
- Reihen auf dem Tisch
- Runde, Stich und Phase

### `PlayerState`
Ein spielerspezifischer Sichtzustand.

Er besteht aus:
- einem `PublicState`
- der eigenen Hand des betroffenen Spielers
- Hilfsinformationen für die aktuelle Entscheidung

### `DeltaPublicState`
Ein einzelner öffentlicher Zustandsübergang während der Auflösung eines Tricks.

Leitidee:

```text
PublicState + DeltaPublicState -> neuer PublicState
```

Ein kompletter Trick ergibt daher eine geordnete Folge von `DeltaPublicState`-Objekten.

## Engine

Die Engine enthält:

- Zustandsdataklassen in `engine/state.py`
- Regeloperationen in `engine/game.py` und `engine/rules.py`
- öffentliche Zustandsoperationen in `engine/public_state_ops.py`
- spielerspezifische Hilfen in `engine/player_state_ops.py`
- Projektionen von `GameState` nach `PublicState` bzw. `PlayerState` in `engine/views.py`

Wichtiger Grundsatz:

- **fachliche Wahrheit** liegt in der Engine
- **Darstellung für Menschen** liegt außerhalb der Engine

### Beispiele für Engine-Verantwortung

- Auswahl einer Karte gegen `PlayerState` validieren
- Reihenwahl validieren
- Trickauflösung starten und fortsetzen
- `DeltaPublicState` erzeugen
- `PublicState` durch Deltas fortschreiben

## Hub

Der Hub hält:
- einen `GameState`
- eine Outbox von Hub-Messages

Der Hub macht im Wesentlichen nur noch dies:

1. Client-Message entgegennehmen
2. passende Engine-Operation aufrufen
3. neue Hub-Messages in die Outbox legen

Typische Hub-Messages sind:
- `StateUpdated`
- `ChooseCardRequested`
- `ChooseRowRequested`
- `TrickResolved`

## Clients

Clients sind austauschbar und verwenden dieselben Hub-Messages.

Aktuell gibt es:
- `CliClient`
- `RandomBotClient`

Später kann ein weiterer Client hinzukommen, ohne den Regelkern zu duplizieren.

Wichtige Regel:

Clients dürfen eigene **Darstellungsstrukturen** besitzen, aber keine eigene Spiellogik.

Erlaubt sind also zum Beispiel:
- sortierte Reihenanzeige in der CLI
- GUI-spezifische Bounding Boxes
- lokale Visualisierungscaches

Nicht in Clients gehören:
- Regelvalidierung, die schon in der Engine lebt
- öffentliche Zustandsfortschreibung außerhalb der Engine
- zweite Varianten der Trickauflösung

## Message-Fluss

Typischer Ablauf eines Stichs:

1. Hub sendet `StateUpdated`
2. Hub sendet pro Spieler `ChooseCardRequested`
3. Clients antworten mit `SubmitCard`
4. Bei Bedarf sendet der Hub `ChooseRowRequested`
5. Betroffener Client antwortet mit `SubmitRowChoice`
6. Hub sendet `TrickResolved`
7. Hub sendet den nächsten `StateUpdated`

`TrickResolved` ist bewusst schlank gehalten. Die eigentliche öffentliche Fortschreibung kann mit der Engine aus dem letzten `PublicState` und den gelieferten Deltas nachvollzogen werden.

## Aktuelle Vereinfachungsrichtung

Die bisherige Entwicklung folgt diesen Leitlinien:

- keine direkte Hub↔Client-Callback-API mehr
- keine Commands-Schicht neben den Messages
- keine zweite Spiellogik in Hub, CLI oder Bot
- zentrale fachliche Arbeit mit `GameState`, `PublicState`, `PlayerState` und `DeltaPublicState`

## Noch bewusst offen

Noch **nicht** das aktuelle Arbeitsthema:
- echter JSON-Transport
- Socket-Kommunikation
- persistente Spielhistorie

Die Architektur ist darauf vorbereitet, aber im Moment steht die saubere Python-interne Struktur im Vordergrund.
