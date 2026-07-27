# GUI-Workbench

Die GUI-Workbench ist ein deterministischer Host für die echte Pygame-Spieloberfläche.
Sie besitzt keinen eigenen Karten-, Reihen- oder Animationsrenderer. Jede Szene wird
als echter `ClientState` aufgebaut und anschließend über denselben `GameFrame` wie
im Netzwerkspiel gerendert.

## Szenen auflisten

```bash
python -m row_taker.gui_workbench --list
```

## Interaktiv untersuchen

```bash
python -m row_taker.gui_workbench card-placed
```

Steuerung:

- `P`: Animation starten oder pausieren
- `Links` / `Rechts`: Präsentationsframe um eins ändern
- `Shift` + `Links` / `Rechts`: Präsentationsframe um zehn ändern
- `Oben` / `Unten`: allgemeinen Animationsframe ändern
- `Home`: beide Frame-Zähler auf null setzen
- `S`: aktuellen Produktionsframe als PNG speichern
- `Esc`: Workbench schließen

Die Fenstergröße kann normal verändert werden. Für jede Größe wird ein neuer
`GameFrame` mit der echten Produktionsgeometrie und den echten Interaktionszielen
erzeugt.

## Einzelnen Frame speichern

```bash
python -m row_taker.gui_workbench card-placed \
  --size 1600x900 \
  --frame 16 \
  --presentation-frame 16 \
  --save screenshots/card-placed-016.png
```

Gespeicherte Frames verwenden standardmäßig die Mausposition `(-1, -1)`, damit
kein zufälliger Hover-Zustand entsteht. Ein Hover kann gezielt reproduziert werden:

```bash
python -m row_taker.gui_workbench choose-card \
  --mouse 180,840 \
  --save screenshots/choose-card-hover.png
```

## Animationsfolge speichern

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

Patch C ergänzt reproduzierbare Abläufe, deren Zustände nicht manuell erfunden
werden. Die Timeline wird mit dem echten `MatchHub`, `GameClientCore`, den
Produktions-Reducern und `GameFrame.handle_event()` erzeugt.

Verfügbare Timelines und ihre Zustände:

```bash
python -m row_taker.gui_workbench --list-timelines
```

Die vollständige Stichauflösung interaktiv öffnen:

```bash
python -m row_taker.gui_workbench --timeline full-trick
```

Zusätzliche Steuerung in einer Timeline:

- `Bild ab`: nächster erzeugter Zustand
- `Bild auf`: vorheriger erzeugter Zustand

Beim Zustandswechsel werden beide Frame-Zähler auf null gesetzt. Dadurch beginnt
die Animation jedes Präsentationsereignisses genauso neu wie beim Wechsel des
vordersten Ereignisses in der echten GUI.

Die gesamte Timeline als PNG-Serie speichern:

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
den Zustand nach der geleerten Präsentationsqueue.
Dessen `PublicState` wird beim Aufbau gegen den tatsächlichen Endzustand des
`MatchHub` geprüft.

## Architekturregel

Die Workbench darf kontrollieren:

- `ClientState`
- Fenstergröße
- Mausposition
- allgemeinen Frame-Zähler
- Präsentationsframe-Zähler
- Ausgabeziel Fenster oder PNG

Sie darf nicht selbst zeichnen oder Produktionsdarstellung nachbauen. Sichtbare
Spielinhalte müssen immer über `GameFrame.render()` und damit über den echten
Produktionsrenderer laufen.

Der Produktionsframe übersetzt den kontrollierten `ClientState` über denselben
`GameVisualStateBuilder` wie die echte GUI. Auch vollständige Präsentationsabläufe
verwenden daher ausschließlich `GameVisualState`, semantische Kartenanker und
die echten Vorher-/Nachher-Snapshots. Eine separate Presentation- oder
Workbench-Darstellung existiert nicht.
