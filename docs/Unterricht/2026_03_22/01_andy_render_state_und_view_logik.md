# An Andy – Warum `render_state()` keine Modelldaten verändern darf

## Das eigentliche Problem

Aktuell war die Gefahr, dass `render_state()` zwei Dinge gleichzeitig erledigt:

1. eine sinnvolle Anzeige-Reihenfolge berechnen
2. diese Reihenfolge zurück in `state.rows` schreiben

Genau das ist architektonisch problematisch.

Eine Funktion mit dem Namen `render_state()` erwartet man als **reine Ausgabefunktion**. Sie soll also nur anzeigen, **wie** etwas dargestellt wird, aber nicht verändern, **was** der eigentliche Spielzustand ist.

## Warum das gefährlich ist

Wenn eine View-Funktion Seiteneffekte hat, entstehen schnell schwer auffindbare Fehler:

- Die Anzeige verändert unbemerkt das Modell.
- Andere Teile des Programms arbeiten plötzlich mit einem umsortierten Zustand.
- Regeln, Tests und Ausgaben beeinflussen sich gegenseitig.
- Ein Bug tritt dann nicht wegen der Spielregel auf, sondern nur deshalb, weil vorher etwas angezeigt wurde.

Gerade bei einem Spielprojekt ist die Trennung wichtig:

- **Engine / Modell:** enthält die Wahrheit über den Spielzustand.
- **View / CLI / GUI:** zeigt diesen Zustand nur an.

## Das frühere Muster, das problematisch war

Ein kritisches Muster wäre zum Beispiel gewesen:

```python
sorted_rows = sorted(state.rows, key=lambda row: row.cards[-1].value if row.cards else 0)
state.rows = sorted_rows
```

Damit würde die Anzeige die Reihenfolge im eigentlichen Zustand überschreiben.

## Was jetzt die bessere Lösung ist

Im aktuellen Stand des Projekts wird stattdessen eine **Anzeigelogik mit Mapping** verwendet. Dabei wird berechnet, in welcher Reihenfolge die Reihen **für die CLI** dargestellt werden sollen, ohne `state.rows` selbst umzubauen.

Das ist die richtige Richtung.

## Warum diese Lösung sauberer ist

Sie trennt zwei Fragen sauber voneinander:

- In welcher Reihenfolge sollen Reihen auf dem Bildschirm oder in der CLI erscheinen?
- In welcher Reihenfolge liegen die Reihen intern im Modell?

Beides muss nicht identisch sein.

## Fachliche Merkhilfe

Eine Render-Funktion sollte möglichst so wirken, als wäre sie mathematisch gesehen fast eine reine Funktion:

- Eingabe: aktueller Zustand
- Ausgabe: Text / Darstellung
- keine Änderung des Zustands

## Fazit

Die wichtigste Lehre aus diesem Punkt ist:

> Eine Ausgabefunktion darf nicht heimlich Spiellogik verändern.

Dass die Anzeige-Reihenfolge jetzt nicht mehr in `state.rows` zurückgeschrieben wird, ist deshalb keine Kleinigkeit, sondern eine echte architektonische Verbesserung.
