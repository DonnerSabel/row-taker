# An Benno – Warum importierbare Module keine Fenster öffnen oder Programme beenden dürfen

## Das eigentliche Architekturproblem

Ein Modul mit einem Namen wie `CardClass.py` erwartet man als Datei, die vor allem Folgendes enthält:

- eine Klasse
- Hilfsfunktionen
- eventuell Konstanten

Was man **nicht** erwartet, ist ein komplettes startendes Programm mit Seiteneffekten beim Import.

Ein problematisches Muster wäre zum Beispiel gewesen:

- `pygame.init()` läuft direkt beim Import
- ein Fenster wird sofort geöffnet
- Demo-Code startet automatisch
- eventuell endet das Programm sogar mit `sys.exit()`

## Warum das schlimm ist

Dann kann schon eine harmlose Zeile wie diese unerwartete Folgen haben:

```python
from row_taker.gui.CardClass import Card
```

Statt nur eine Klasse zu importieren, könnte plötzlich:

- ein Fenster aufgehen
- eine Event-Schleife starten
- das Programm in einen unerwarteten Zustand geraten
- oder sogar der Prozess beendet werden

Das ist kein Stilproblem, sondern ein echter Architekturfehler.

## Wo das später Probleme macht

So ein Moduldesign schadet besonders bei:

- GUI-Zusammenbau
- Tests
- Wiederverwendung der Klasse in anderen Dateien
- Importen aus `main.py`, `spielfeld.py` oder weiteren GUI-Teilen

Ein gutes Modul muss importierbar sein, **ohne** dabei das Programm zu starten.

## Was die saubere Lösung ist

Im aktuellen Repo ist dieser Punkt bereits deutlich besser gelöst:

- `card.py` enthält nur die Kartenklasse
- `main.py` enthält die Startlogik
- `__main__.py` dient als Einstiegspunkt

So muss es sein.

## Die Regel dahinter

Ein Modul sollte beim Import möglichst nur Definitionen bereitstellen:

- Klassen
- Funktionen
- Konstanten

Startcode gehört an genau einen bewusst gewählten Einstiegspunkt.

## Gute Merkhilfe

Man kann sich folgende Regel merken:

> Import ist Laden, nicht Starten.

Wer etwas importiert, möchte normalerweise nur Code verfügbar machen, aber noch nichts ausführen, was Fenster öffnet, Schleifen startet oder das Programm beendet.

## Fazit

Die Trennung von Kartenklasse und Startlogik ist wichtig, weil sie das Projekt wartbarer macht. Sie ist besonders wertvoll, wenn später mehrere GUI-Dateien zusammenspielen oder wenn Tests auf einzelne GUI-Komponenten geschrieben werden.
