# GUI-Workbench

Die GUI-Workbench ist ein deterministischer Host für **alle drei echten
Pygame-Oberflächen**. Sie besitzt keine eigene Zeichenlogik. Jedes Szenario wird
durch genau den Prepared Frame gerendert, den auch `GuiApp` verwendet:

```text
WorkbenchScenario
    ├── ConnectWorkbenchScenario → ConnectFrame
    ├── LobbyWorkbenchScenario   → LobbyFrame
    └── GameWorkbenchScenario    → GameFrame
```

Die Workbench kontrolliert nur Zustand, Fenstergröße, Mausposition,
Frame-Zähler und Ausgabeziel.

## Szenen auflisten

```bash
python -m row_taker.gui_workbench --list
```

Die Ausgabe ist in `[connect]`, `[lobby]` und `[game]` gegliedert.

Beispiele:

```bash
python -m row_taker.gui_workbench connect-error
python -m row_taker.gui_workbench lobby-bot-name-edit
python -m row_taker.gui_workbench card-placed
```

Die Connect-Szenen decken Standardwerte, ungültige Eingaben,
Verbindungsfehler und lange Feldwerte ab. Die Lobby-Szenen decken leere und
volle Lobbys, Sitzplatzauswahl, Bot-Namenseingabe und lange Namen ab.

## Interaktiv untersuchen

Steuerung:

- `P`: Animation starten oder pausieren
- `Links` / `Rechts`: Präsentationsframe um eins ändern
- `Shift` + `Links` / `Rechts`: Präsentationsframe um zehn ändern
- `Oben` / `Unten`: allgemeinen Animationsframe ändern
- `Home`: beide Frame-Zähler auf null setzen
- `S`: aktuellen Produktionsframe als PNG speichern
- `Esc`: Workbench schließen

Die Fenstergröße kann normal verändert werden. Für jede Größe wird ein neuer
Prepared Frame mit der echten Produktionsgeometrie und den echten
Interaktionszielen erzeugt.

## Einzelnen Frame speichern

```bash
python -m row_taker.gui_workbench lobby-long-names \
  --size 1600x900 \
  --save screenshots/lobby-long-names.png
```

Gespeicherte Frames verwenden standardmäßig die Mausposition `(-1, -1)`, damit
kein zufälliger Hover-Zustand entsteht. Ein Hover kann gezielt reproduziert
werden:

```bash
python -m row_taker.gui_workbench connect-default \
  --mouse 700,650 \
  --save screenshots/connect-hover.png
```

## Animationsfolge speichern

Für Spiel-Präsentationen können mehrere Frames ausgegeben werden:

```bash
python -m row_taker.gui_workbench row-taken \
  --save-dir screenshots/row-taken
```

Ohne `--frames` werden die für die Szene hinterlegten interessanten Frames
gerendert. Eine eigene Auswahl ist ebenfalls möglich:

```bash
python -m row_taker.gui_workbench row-taken \
  --frames 0,4,8,12,16,24,32 \
  --save-dir screenshots/row-taken
```

## Vollständige Timeline untersuchen

Die Timeline wird mit dem echten `MatchHub`, `GameClientCore`, den
Produktions-Reducern und `GameFrame.handle_event()` erzeugt.

```bash
python -m row_taker.gui_workbench --list-timelines
python -m row_taker.gui_workbench --timeline full-trick
```

Zusätzliche Steuerung in einer Timeline:

- `Bild ab`: nächster erzeugter Zustand
- `Bild auf`: vorheriger erzeugter Zustand

Beim Zustandswechsel werden beide Frame-Zähler auf null gesetzt. Die gesamte
Timeline kann als PNG-Serie gespeichert werden:

```bash
python -m row_taker.gui_workbench --timeline full-trick \
  --save-dir screenshots/full-trick
```

Einen einzelnen Zustand und Frame speichern:

```bash
python -m row_taker.gui_workbench --timeline full-trick \
  --step 5 --frame 16 --presentation-frame 16 \
  --save screenshots/row-taken-016.png
```

Die Timeline navigiert direkt über `PresentationStep`-Objekte und enthält auch
den Zustand nach der geleerten Präsentationsqueue. Dessen `PublicState` wird
beim Aufbau gegen den tatsächlichen Endzustand des `MatchHub` geprüft.

## Architekturregel

Die Workbench darf kontrollieren:

- `ConnectFormState` oder `ClientState`
- Fenstergröße
- Mausposition
- allgemeinen Frame-Zähler
- Präsentationsframe-Zähler
- Ausgabeziel Fenster oder PNG

Sie darf nicht selbst zeichnen oder Produktionsdarstellung nachbauen. Sichtbare
Inhalte müssen immer über `ConnectFrame.render()`, `LobbyFrame.render()` oder
`GameFrame.render()` laufen.

Die festen Spielszenarien erzeugen echte `ClientState`-Objekte. Für
Präsentationsabläufe werden die vorhandenen Reducer und der echte lokale
Trick-Resolver verwendet. Eine separate Workbench-Darstellung existiert nicht.
