# Architektur

## Zweck dieses Dokuments

Dieses Dokument beschreibt die Zielarchitektur des Projekts in kompakter Form.
Es darf dem aktuellen Codezustand voraus sein.

Für die ausführlichere Begründung und die wichtigen Designentscheidungen ist
`docs/row_taker_design_decisions.md` maßgeblich.

---

## Leitidee

Das Projekt trennt bewusst vier Ebenen:

- **Engine/Game** – kennt die fachlichen Regeln und Zustandsübergänge
- **Engine/Lobby** – kennt die minimale Sitzplatz- und Lobbylogik
- **Server** – orchestriert Prozesse, Teilnehmer und Protokollfluss
- **Clients** – verwenden dieselbe Engine lokal zur Interpretation und Darstellung

Der Server ist **nicht** der zweite Regelkern.
Die fachliche Wahrheit liegt in der Engine.

---

## Zentrale Zustände

### `GameState`

Der vollständige fachliche Spielzustand.

Er enthält unter anderem:
- Spieler mit Händen und Punkteständen
- Reihen auf dem Tisch
- Deck
- Phasen- und Auflösungskontext

Der `GameState` ist kein reguläres Spielfluss-Nachrichtenformat.
Er ist ein Engine-Zustand.

### `PublicState`

Der fachliche öffentliche Zustand des Spiels.

Er enthält nur Informationen, die alle sehen dürfen.

### `PlayerState`

Ein spielerspezifischer Sichtzustand.

Er besteht fachlich aus:
- öffentlichem Zustand
- eigener Hand
- entscheidungsrelevanten Zusatzinformationen

---

## Protokollgrundsatz

Das Spielprotokoll soll **minimal, aber fachlich vollständig** sein.

Die zentralen Synchronisationspunkte sind:
- gemeinsamer Spiel- oder Rundenstart mit denselben Ausgangsdaten
- vollständige Offenlegung aller gespielten Karten eines Stichs
- Reihenwahl, wenn erforderlich
- administrative Nachrichten wie Spielende, Abbruch, Disconnect oder Spieler weg

Nicht Ziel des Spielfluss-Protokolls sind:
- permanente Zustands-Snapshots
- Zwischenstände jeder Mikroauflösung
- Darstellungshilfen, die lokal aus der Engine berechnet werden können

Kurz:

**Arm im Protokoll, reich in der Engine.**

---

## Wichtige Folge daraus

Nach den Synchronisationspunkten wird der sichtbare weitere Ablauf des Stichs lokal
in jedem Prozess mit Hilfe der Engine berechnet.

Dazu gehören insbesondere:
- normale Kartenplatzierung
- Überlauf einer Reihe
- kleinste Karte mit notwendiger Reihenwahl
- betroffener Spieler
- genommene Karten und daraus folgende Hornochsen

Diese fachliche Auflösung soll nicht durch eine Explosion von Hub- oder
Server-Messages beschrieben werden.

---

## `CardsRevealed`

Die Offenlegung der gespielten Karten ist fachlich eine vollständige Sammlung aller
gewählten Karten eines Stichs.

Wichtig:

- die JSON-Liste ist nur ein Transportgefäß
- ihre Reihenfolge hat keine fachliche Bedeutung
- die Engine bestimmt lokal selbst die regelkonforme Auflösungsreihenfolge

---

## Empfang, Anwendung, Darstellung

Durch TCP mit zeilenbasiertem Framing bleibt die Nachrichtenreihenfolge pro
Verbindung erhalten.

Daraus folgt aber **nicht**, dass eine GUI eingehende Nachrichten sofort sichtbar
"abspielen" muss.

Jeder Client muss sauber trennen zwischen:

1. **empfangen**
2. **fachlich anwenden**
3. **darstellen / animieren**

Diese Trennung ist zentral für robuste GUI-Arbeit.
Sie ist inzwischen nicht mehr nur Zielbild, sondern bereits im aktuellen Clientzuschnitt angelegt:
Nachrichten werden geordnet empfangen, kontrolliert angewendet und anschließend über eine clientseitige
Presentation-Schicht sichtbar gemacht.

---

## Trickauflösung: Resolver / Stepper

Die Zielarchitektur für die Trickauflösung ist ein lokaler **Resolver / Stepper**.

Das bedeutet:
- die Engine erzeugt ein lokales Auflösungsobjekt
- dieses liefert jeweils den nächsten fachlichen Schritt
- bei externer Wahl, insbesondere Reihenwahl, pausiert es sauber
- nach der Wahl läuft die Auflösung weiter

Die GUI oder CLI beobachtet diese fachlichen Schritte.
Sie wird nicht per Callback aus der Engine heraus gesteuert.

Jeder clientseitige Präsentationsschritt enthält zusätzlich zum
`PresentationEvent` zwei unveränderliche fachliche Snapshots:

- `public_state_before`
- `public_state_after`

Rein erklärende Ereignisse besitzen denselben Vorher- und Nachher-Zustand.
Fachlich verändernde Ereignisse wie Kartenablage oder Reihenübernahme tragen
den Zustand vor und nach dem zugehörigen Engine-Schritt. Der Client verwaltet
intern ausschließlich Queues solcher `PresentationStep`-Objekte. GUI, CLI und
Workbench greifen direkt auf
`presentation_steps`, `pending_presentation_steps` und
`current_presentation_step` zu. Eine parallele Event-Queue existiert nicht.

---

## GUI- und CLI-Prinzip

GUI und CLI dürfen eigene Darstellungsstrukturen besitzen.
Sie dürfen aber keine eigene Spiellogik neu erfinden.

Erlaubt sind zum Beispiel:
- Bounding Boxes
- Sortier- oder Layout-Hilfen
- Animationszustände
- Darstellungscaches

Nicht in Clients gehören:
- zweite Regelvalidierung
- zweite Trickauflösung
- lokale Sonderlogik, die der Engine widerspricht


### Produktionsframe, GameVisualState und GUI-Workbench

Die aktuelle Pygame-GUI übersetzt den `ClientState` an der Frame-Grenze einmalig
in einen pygame-unabhängigen `GameVisualState`:

```text
ClientState
    ↓
GameVisualStateBuilder
    ↓
GameVisualState
    ↓
GameFrame
    ├── BoardGeometry
    ├── GameScreenTargets
    └── Produktionsrenderer
```

Der `GameVisualState` ist die vollständige semantische Beschreibung des
sichtbaren Spielbildschirms. Er enthält Reihen, Spieler, Handkarten,
Interaktionsmöglichkeiten, Statusinformationen, Präsentationspanel und
semantische Kartenbewegungen. Er enthält keine pygame-Objekte, Pixelkoordinaten,
Fonts, Farben, Protokollnachrichten oder Client-Actions.

Alle Präsentationsereignisse werden vor dem Rendering in vollständige visuelle
Zustände übersetzt. Zustandsverändernde Schritte verwenden die unveränderlichen
`public_state_before`- und `public_state_after`-Snapshots und eine semantische
Transition. Der Renderer kennt keine `PresentationEvent`-Typen und keinen
`ClientState`. Die frühere `PresentationVisuals`-Kompatibilitätsschicht ist
entfernt.

Ein vollständig vorbereiteter `GameFrame` besitzt gemeinsam:

- den verwendeten `GameVisualState`
- die für die Fenstergröße berechnete `BoardGeometry`
- die daraus und aus der Mausposition erzeugten `GameScreenTargets`
- die allgemeinen und presentationsbezogenen Frame-Zähler

Geometrie und Interaktionsziele werden einmal gemeinsam vorbereitet und danach
nicht unabhängig voneinander ausgetauscht. Bei einer Größenänderung wird ein
neuer `GameFrame` erzeugt.

Die GUI-Workbench kontrolliert Fenstergröße, Mausposition, Zustände und
Frame-Zähler. Sie benutzt denselben `GameFrame`, dieselbe Target-Erzeugung und
denselben Produktionsrenderer wie die echte GUI. Sie besitzt keine eigene
Karten-, Reihen- oder Animationsdarstellung.

Die festen Workbench-Szenarien erzeugen echte `ClientState`-Objekte. Für
Präsentationsabläufe werden die vorhandenen Reducer und der echte lokale
Trick-Resolver verwendet, sodass nicht parallel eine zweite Darstellungslogik
entsteht. Der Workbench-Code darf nur die Eingaben des Produktionsframes und das
Ausgabeziel kontrollieren.

---

## Debugging

Das Projekt trennt bewusst:
- **Spielfluss-Protokoll**
- **optionales reichhaltiges Debugging**

Im normalen Spielfluss bleibt das Protokoll minimal.

Im Debugging darf bewusst "volle Bazooka" erlaubt sein, zum Beispiel:
- vollständiger `GameState`
- weitere Projektionen
- interner Serverkontext
- semantische Schrittspuren

Wichtig ist nur:
- Debugging ist Zusatzsicht
- Debugging ersetzt nicht die fachliche Vollständigkeit des Spielfluss-Protokolls

---

## Praktische Leitfrage

Bei späteren Umbauten sollte immer zuerst gefragt werden:

- bleibt die Engine der eigentliche Bedeutungsträger?
- bleibt das Protokoll minimal, aber vollständig?
- bleibt die Reihenfolge von empfangen, anwenden und darstellen sauber getrennt?
- bleibt die Trickauflösung als Resolver / Stepper lokal in der Engine?

Wenn hier ein Nein auftaucht, läuft die Architektur sehr wahrscheinlich in die falsche
Richtung.

## Presentation-Schicht

Clients leiten aus lokalen Resolver-/Stepper-Schritten eine GUI-neutrale Folge
von `PresentationEvent`-Objekten ab.

Diese Schicht ist die Andockfläche für CLI und GUI.

Wichtig:

- sie enthält keine GUI-Objekte
- `card_value` bleibt die fachliche Karten-ID
- eine GUI verwaltet ihre eigenen Objekte selbst, typischerweise über ein Mapping
  wie `card_value -> GuiCard`
- die CLI rendert dieselbe Schicht nur in Textform

## SessionEnded und Server-Shutdown

Wenn ein Teilnehmer die Sitzung beendet, verschickt der Server eine
`SessionEnded`-Nachricht an alle übrigen Clients.

Folgen:

- alle übrigen Clients beenden sich daraufhin lokal
- dazu gehören ausdrücklich auch Bots
- der Server markiert die Sitzung als beendet
- nachdem danach keine Teilnehmerverbindungen und keine laufenden Bot-Prozesse
  mehr übrig sind, fährt der Server automatisch herunter

Die Shutdown-Policy hängt damit am fachlichen Zustand **SessionEnded** und nicht
an einer Sonderregel wie „keine Humans mehr da“.

## Logging

Server, CLI und Bot-Prozesse verwenden Python-Logging mit konfigurierbarem
Log-Level und optionalen Logdateien.

Der Server akzeptiert `--log-level` und `--log-file`.
CLI-Clients akzeptieren ebenfalls `--log-level` und `--log-file`.
Lokal gestartete Bots übernehmen den Log-Level des Servers und erhalten bei
gesetztem Server-Logpfad automatisch eine abgeleitete Bot-Logdatei.
