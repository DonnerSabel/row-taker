# An Benno und Laurin – Warum die GUI eine klare Dateistruktur braucht

## Ausgangsproblem

Bei kleinen Experimenten landet anfangs oft vieles in wenigen Dateien. Für ein wachsendes Projekt wird das aber schnell unübersichtlich.

Ein typischer unsauberer Zustand wäre zum Beispiel:

- `gui/__main__.py` startet irgendein anderes Modul direkt
- `gui/main.py` ist leer oder kaum genutzt
- eine Datei enthält gleichzeitig Klasse **und** Demo-Programm
- eine andere Datei enthält ebenfalls Klasse **und** Startcode

So etwas funktioniert kurzfristig, wird aber später schwer wartbar.

## Zielstruktur

Die sinnvolle Zielstruktur ist:

```text
src/row_taker/gui/
├── __init__.py
├── __main__.py
├── main.py
├── card.py
├── spielfeld.py
└── constants.py
```

## Rolle der einzelnen Dateien

### `card.py`
Enthält nur die Kartenklasse.

### `spielfeld.py`
Enthält nur die Spielfeldklasse.

### `constants.py`
Enthält zentrale Konstanten, damit keine unnötigen Magic Numbers im Projekt verstreut sind.

### `main.py`
Enthält die eigentliche Anwendungslogik, zum Beispiel eine Funktion `run()`.

### `__main__.py`
Ist der einzige definierte Starteinstieg für `python -m row_taker.gui`.

## Warum das besser ist

Diese Struktur bringt mehrere Vorteile:

- Verantwortlichkeiten sind klar getrennt.
- Klassen können sauber importiert und wiederverwendet werden.
- Tests und spätere Umbauten werden einfacher.
- Man findet schneller, wo Startlogik hingehört und wo nicht.
- Die GUI kann wachsen, ohne dass eine Datei alles gleichzeitig macht.

## Was man im aktuellen Repo schon positiv sieht

Im ZIP ist diese Richtung bereits umgesetzt:

- `card.py` enthält die Kartenklasse
- `spielfeld.py` enthält die Spielfeldklasse
- `constants.py` bündelt Konstanten
- `main.py` enthält `run()`
- `__main__.py` ruft `run()` als Einstiegspunkt auf

Das ist eine klare Verbesserung gegenüber einer Struktur, in der Klasse, Demo und Startcode vermischt werden.

## Merksatz

> Eine Datei sollte möglichst nur eine klar erkennbare Hauptaufgabe haben.

Gerade in GUI-Projekten spart das später viel Zeit.

## Fazit

Die neue Struktur ist nicht nur „schöner“, sondern fachlich sinnvoll. Sie ist ein wichtiger Schritt von einem ersten Experiment hin zu einem sauber aufgebauten Softwareprojekt.
