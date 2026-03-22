# Einführung in Pygame

Für das Projekt „6 nimmt!“.

## Lernziel

Nach dieser Einführung sollen die Schüler:

- Pygame installieren können
- ein erstes Fenster öffnen können
- die Grundidee der Spielschleife verstehen
- einfache Grafiken und Bilder anzeigen können
- erkennen, welche Bausteine später für das Kartenspiel benötigt werden

## Einführung

**Pygame** ist eine Python-Bibliothek, mit der man Spiele programmieren kann.

Sie stellt einfache Funktionen bereit für:

- Fenster öffnen
- Grafiken anzeigen
- Maus und Tastatur abfragen
- einfache Animationen

Viele bekannte Indie-Spiele sind mit ähnlichen Bibliotheken entstanden.

Für unser Projekt brauchen wir vor allem:

- ein **Fenster**
- eine **Spielschleife**
- das **Zeichnen von Karten**

> **Merksatz:** Für unser Projekt sind vor allem Fenster, Spielschleife und Kartendarstellung wichtig.

## Installation

Im Projektordner mit aktivierter virtueller Umgebung:

```bash
pip install pygame
```

Test:

```python
import pygame
print(pygame.ver)
```

## Das erste Fenster

Minimalbeispiel:

```python
import pygame

# pygame starten
pygame.init()

# Fenster erzeugen
screen = pygame.display.set_mode((800, 600))

# Fenstertitel
pygame.display.set_caption("Row Taker")

# Programm läuft solange running True ist
running = True

while running:

    # Events, z. B. Fenster schließen
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

pygame.quit()
```

## Beobachtung

Wenn ihr das Programm startet, öffnet sich ein **leeres Fenster**.

## Die Spielschleife

Fast jedes Spiel funktioniert mit einer **Game Loop**.

Sie läuft viele Male pro Sekunde.

Schema:

```text
while Spiel_läuft:

    Eingaben verarbeiten
    Spielzustand aktualisieren
    Bildschirm neu zeichnen
```

In Pygame sieht das so aus:

```python
while running:

    # Eingaben
    for event in pygame.event.get():
        ...

    # Spiel aktualisieren
    ...

    # Zeichnen
    ...

    pygame.display.flip()
```

`flip()` zeigt das neu gezeichnete Bild an.

> **Merksatz:** Pygame stellt keine fertige Spielschleife bereit. Die Schleife wird von uns selbst geschrieben.

### Saubere Struktur mit einer Game-Klasse

Für kleine Beispiele kann man die Spielschleife direkt im Hauptprogramm schreiben. Für ein größeres Projekt wie „6 nimmt!“ ist es aber sinnvoll, das Spiel in einer Klasse zu kapseln.

Dadurch wird der Code übersichtlicher:

- `handle_events()` verarbeitet Eingaben
- `update()` verändert den Spielzustand
- `draw()` zeichnet alles auf den Bildschirm
- `run()` enthält die eigentliche Spielschleife

```python
import pygame


class Game:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Row Taker")
        self.clock = pygame.time.Clock()
        self.running = True

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update(self) -> None:
        pass

    def draw(self) -> None:
        self.screen.fill((0, 120, 0))
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)


def main() -> None:
    game = Game()
    game.run()
    pygame.quit()


if __name__ == "__main__":
    main()
```

## Etwas auf den Bildschirm zeichnen

Wir können den Bildschirm einfärben.

```python
screen.fill((30, 120, 30))
```

RGB-Farben:

```text
(255, 0, 0)   rot
(0, 255, 0)   grün
(0, 0, 255)   blau
```

Beispiel:

```python
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 120, 0))

    pygame.display.flip()
```

## Beobachtung

Jetzt ist das Fenster grün.

## Ein Bild laden

Pygame kann PNG direkt laden.

Beispielstruktur:

```text
assets/
    card.png
```

Code:

```python
card = pygame.image.load("assets/card.png")
```

Bild anzeigen:

```python
screen.blit(card, (100, 100))
```

`blit` bedeutet: Zeichne dieses Bild auf den Bildschirm.

Beispiel:

```python
card = pygame.image.load("assets/card.png")

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 120, 0))

    screen.blit(card, (100, 100))

    pygame.display.flip()
```

## Bilder skalieren

Karten brauchen eine feste Größe.

```python
card = pygame.transform.scale(card, (120, 180))
```

Dann kann man mehrere Karten zeichnen:

```python
screen.blit(card, (100, 300))
screen.blit(card, (250, 300))
screen.blit(card, (400, 300))
```

## Text anzeigen

Damit können wir später Kartennummern anzeigen.

```python
font = pygame.font.Font(None, 36)

text = font.render("23", True, (0, 0, 0))

screen.blit(text, (110, 310))
```

## Beispiel

Eine einfache Karte:

```python
import pygame

pygame.init()

screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Row Taker")

font = pygame.font.Font(None, 40)

running = True

while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 120, 0))

    pygame.draw.rect(screen, (255, 255, 255), (100, 250, 120, 180))
    pygame.draw.rect(screen, (0, 0, 0), (100, 250, 120, 180), 2)

    number = font.render("23", True, (0, 0, 0))
    screen.blit(number, (150, 260))

    pygame.display.flip()

pygame.quit()
```

## Beobachtung

Eine Spielkarte wird angezeigt.

## Das brauchen wir für „6 nimmt!“

Für unser Projekt müssen wir später:

- Karten **anzeigen**
- Karten **anklicken**
- Karten **verschieben**
- Karten **in Reihen legen**

Dafür brauchen wir vor allem:

- `pygame.Rect`
- Maus-Events
- mehrere Kartenobjekte

Das bauen wir Schritt für Schritt auf.

## Nächster Schritt im Projekt

Als Nächstes werden wir:

1. eine **Card-Klasse** schreiben
2. mehrere Karten auf dem Tisch anzeigen
3. Karten mit der Maus anklicken

Das ist bereits ein großer Teil des Spiels.

## Zusammenfassung

- Pygame kann Fenster, Bilder, Text und Eingaben verarbeiten.
- Die Spielschleife ist das Grundgerüst jedes Spiels.
- Für größere Projekte ist eine `Game`-Klasse sinnvoll.
- Für unser Kartenspiel sind Kartenanzeige und Maussteuerung die nächsten wichtigen Schritte.

> **Merksatz:** Wer die Spielschleife, das Zeichnen und die Event-Verarbeitung versteht, hat die Grundlage für das gesamte Projekt gelegt.
