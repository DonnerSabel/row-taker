# Benno – Kartenposition, Bounding Box und Punktprüfung

## Worum es hier geht

Bei einer anklickbaren Karte gibt es eine wichtige Frage:

Wenn geprüft wird, ob ein Mauspunkt auf der Karte liegt, in welchem Koordinatensystem passiert diese Prüfung eigentlich?

Zum Beispiel bei einer Methode wie:

```python
def contains_point(self, x: int, y: int) -> bool:
```

sind zwei Dinge unklar:

1. Sind `x` und `y` **Fensterkoordinaten**?  
   Also genau die Koordinaten, die vom Mausklick im Spielfenster kommen?

2. Oder sind `x` und `y` **kartenlokale Koordinaten**?  
   Also relativ zur linken oberen Ecke der Karte?

Diese Unterscheidung ist wichtig, weil sonst später leicht Fehler entstehen.

---

## Warum das überhaupt ein Thema ist

Eine Karte liegt nicht irgendwo „im Nichts“, sondern an einer bestimmten Stelle im Spielfenster.

Wenn also ein Mausklick bei `(500, 300)` passiert, dann muss die Karte wissen:

- Wo bin ich im Fenster?
- Gehört dieser Punkt zu mir?
- Liegt der Punkt vielleicht zwar in meiner rechteckigen Bounding Box, aber eigentlich in einer abgeschnittenen Ecke?

Damit eine Karte das prüfen kann, braucht sie ihre **eigene Position und Größe**.

---

## Problem an `self.x` und `self.y`

Im bisherigen Entwurf wird die Position über `self.x` und `self.y` gespeichert.

Das funktioniert zwar grundsätzlich, hat aber einige Nachteile:

- `self.x` und `self.y` gehen leicht zwischen anderen Attributen unter.
- Die Position ist nicht gemeinsam mit der Größe gebündelt.
- Man muss sich selbst merken:
  - Was bedeutet `x` genau?
  - Ist das die linke obere Ecke?
  - Wo stehen Breite und Höhe?
- Man erfindet damit eine eigene Mini-Struktur, obwohl Pygame dafür bereits etwas Passendes hat.

Gerade in einer GUI ist die Position eines Objekts aber **kein Nebendetail**, sondern ein zentrales Attribut.

Darum sollte das in der Klasse auch deutlich sichtbar modelliert werden.

---

## Bessere Lösung: `self.rect`

In Pygame gibt es für genau diesen Zweck den Typ `Rect`.

Ein `Rect` speichert zusammen:

- Position
- Breite
- Höhe

Zum Beispiel:

```python
self.rect = pygame.Rect(x, y, width, height)
```

oder:

```python
self.rect = pygame.Rect((x, y), (width, height))
```

Das ist viel besser als getrennte Attribute wie `self.x`, `self.y`, `self.width`, `self.height`, weil alles logisch zusammengehört.

---

## Warum `Rect` hier gut passt

Ein `Rect` ist in Pygame der natürliche Typ für rechteckige Bereiche.

Damit kann man sehr gut arbeiten:

- `self.rect.x`
- `self.rect.y`
- `self.rect.width`
- `self.rect.height`
- `self.rect.topleft`
- `self.rect.center`

Außerdem bringt `Rect` bereits nützliche Methoden mit, zum Beispiel:

```python
self.rect.collidepoint(point)
```

Damit kann man sehr einfach prüfen, ob ein Punkt überhaupt in der rechteckigen Bounding Box liegt.

Das ist für die Kartenklasse ideal.

---

## Wichtige Unterscheidung: Bounding Box ist nicht die ganze Karte

Die Karte ist optisch an den Ecken abgerundet.

Deshalb gilt:

**Bounding Box != tatsächliche Kartenform**

Die Bounding Box ist nur das umgebende Rechteck.

Das ist für eine erste grobe Prüfung sehr nützlich, aber noch nicht die endgültige Antwort.

Ein Punkt kann also:

- **in der Bounding Box liegen**
- aber **trotzdem nicht wirklich zur Karte gehören**

zum Beispiel in einer abgeschnittenen Ecke.

Darum ist eine zweistufige Prüfung sinnvoll:

1. Liegt der Punkt in der Bounding Box?
2. Wenn ja: Gehört er auch wirklich zur Kartenform?

---

## Welche Koordinaten sollte `contains_point(...)` bekommen?

Hier ist die wichtigste Entwurfsentscheidung:

Die Methode

```python
contains_point(...)
```

sollte **Fensterkoordinaten** bekommen.

Also genau die Koordinaten, die direkt vom Mausklick kommen.

Zum Beispiel:

```python
point = event.pos
if card.contains_point(point):
    ...
```

Das ist für den aufrufenden Code am einfachsten und am lesbarsten.

Der Aufrufer muss dann nichts umrechnen.

---

## Warum nicht direkt kartenlokale Koordinaten?

Man könnte natürlich auch lokal prüfen, also relativ zur Karte.

Das wäre für die Geometrie oft bequem.

Aber dann müsste der aufrufende Code zuerst umrechnen:

```python
local_x = mouse_x - card.rect.x
local_y = mouse_y - card.rect.y
```

Wenn das überall außerhalb der Karte passiert, verteilt sich diese Logik an viele Stellen.

Besser ist deshalb:

- **außen:** einfache Schnittstelle mit Fensterkoordinaten
- **innen:** Umrechnung in lokale Koordinaten

So bleibt der Aufrufer einfach und die Karte kümmert sich selbst um ihre Geometrie.

---

## Noch eine Verbesserung: Punkt nicht als `x, y`, sondern als Tupel

Auch diese Signatur ist nicht ideal:

```python
def contains_point(self, x: int, y: int) -> bool:
```

Besser wäre:

```python
def contains_point(self, point: tuple[int, int]) -> bool:
```

Warum?

Weil ein Punkt in Pygame normalerweise als zusammengehöriges Koordinatenpaar behandelt wird.

Auch `event.pos` ist bereits so aufgebaut.

Das hat Vorteile:

- Punktdaten bleiben zusammen.
- Die Methode passt direkt zu Mausklick-Daten.
- Weniger einzelne Parameter.
- Der Code wirkt klarer und näher an Pygame.

---

## Empfohlener Aufbau

Die Kartenklasse sollte ihre Lage und Größe über `self.rect` speichern.

Die Punktprüfung sollte mit Fensterkoordinaten arbeiten.

Intern kann dann in lokale Koordinaten umgerechnet werden.

Ein sinnvoller Aufbau wäre also:

```python
class CardSprite:
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect

    def contains_point(self, point: tuple[int, int]) -> bool:
        if not self.rect.collidepoint(point):
            return False

        local_point = (point[0] - self.rect.x, point[1] - self.rect.y)
        return self.contains_local_point(local_point)

    def contains_local_point(self, point: tuple[int, int]) -> bool:
        ...
```

---

## Warum dieser Aufbau gut ist

### 1. Die Position der Karte ist klar sichtbar

Die Lage der Karte steckt nicht versteckt irgendwo in `self.x` und `self.y`, sondern gebündelt in einem zentralen Attribut:

```python
self.rect
```

Das macht sofort klar: Diese Karte hat eine Position und eine Größe im Fenster.

### 2. Die Klasse passt besser zu Pygame

Man nutzt die vorhandenen Strukturen der Bibliothek, statt eigene Ersatzlösungen zu bauen.

### 3. Die Schnittstelle ist angenehm für den Aufrufer

Ein Mausklick kann direkt geprüft werden.

### 4. Die Geometrie bleibt sauber getrennt

- Bounding Box: grobe Vorprüfung
- echte Kartenform: genaue Prüfung

---

## Praktische Denkweise für die Karte

Die Karte sollte sozusagen selbst sagen können:

- „Das ist mein Rechteck im Fenster.“
- „Dieser Punkt liegt in meinem Rechteck.“
- „Dieser Punkt liegt wirklich auf meiner sichtbaren Form.“
- „Ich kann globale Koordinaten intern in lokale Koordinaten umrechnen.“

Das ist genau die Art von Verantwortung, die zu einer Kartenklasse passt.

---

## Empfehlung

Für die weitere Arbeit ist daher zu empfehlen:

### Statt
- `self.x`
- `self.y`

### besser
- `self.rect`

und

### statt

```python
def contains_point(self, x: int, y: int) -> bool:
```

### besser

```python
def contains_point(self, point: tuple[int, int]) -> bool:
```

---

## Fazit

Die Position einer Karte ist ein zentrales Attribut und sollte deshalb auch klar und passend modelliert werden.

Die beste Lösung ist hier:

- Kartenposition und Kartengröße über `pygame.Rect`
- Punktprüfung mit Fensterkoordinaten
- intern Umrechnung in lokale Koordinaten
- zusätzliche genaue Prüfung für die abgerundete Kartenform

So wird der Code:

- verständlicher
- näher an Pygame
- leichter erweiterbar
- robuster bei Klick- und Layoutlogik
