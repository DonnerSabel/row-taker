# Arbeitsaufträge für morgen – GUI- und Netzwerk-Gruppe

## Ziel dieser Hinweise

Diese Hinweise sollen Ihnen helfen, morgen **möglichst zielgerichtet** zu arbeiten.

Die größte Gefahr bei solchen Aufgaben ist nicht, dass etwas technisch unmöglich wäre.  
Die größere Gefahr ist, dass man zu viele Dinge gleichzeitig anfängt und sich dadurch verzettelt.

Darum geht es hier vor allem um:

- klare Zuständigkeiten
- einfache Schnittstellen
- kleine, überprüfbare Zwischenschritte
- ein realistisches Minimalziel

---

# 1. GUI-Gruppe: technische Richtung früh festlegen

Wenn mehrere Personen gleichzeitig an einer GUI arbeiten, ist es wichtig, dass nicht drei verschiedene Ideen parallel halb umgesetzt werden.

Darum sollte die Richtung früh festgelegt werden.

## Wichtigste Grundidee

Die Karte braucht genau zwei Dinge:

- eine **Bounding Box**
- eine Methode zur Punktprüfung, also zum Beispiel `contains_point(...)`

Die Bounding Box ist das Rechteck, das die Karte umgibt.

Die Methode `contains_point(...)` beantwortet die wichtigere Frage:

**Gehört ein bestimmter Punkt wirklich zur Karte?**

Das ist nicht ganz dasselbe.

---

## Warum diese Trennung sinnvoll ist

Bei einer Karte mit abgerundeten Ecken kann ein Punkt zwar im umgebenden Rechteck liegen, aber trotzdem nicht wirklich auf der sichtbaren Kartenfläche.

Deshalb ist folgende Trennung sehr sinnvoll:

- **Rechteck für Layout**
- **echte Kartenform für Treffererkennung**

Das Modell wird dadurch deutlich sauberer.

---

## Wichtige Regel für die Mauslogik

Die Mauslogik soll **niemals direkt** die Bounding Box abfragen.

Stattdessen soll sie **immer** `contains_point(...)` verwenden.

Warum ist das wichtig?

Weil dadurch nur **eine** Stelle darüber entscheidet, ob ein Punkt wirklich zur Karte gehört.

Das hat mehrere Vorteile:

- weniger doppelte Logik
- weniger Fehler
- spätere Änderungen sind einfacher
- die Verantwortung bleibt in der Kartenklasse

---

## Möglicher Aufbau

Zum Beispiel so:

```python
class CardSprite:
    def get_bounding_rect(self) -> pygame.Rect:
        ...

    def contains_point(self, point: tuple[int, int]) -> bool:
        ...
```

Dann ist klar:

- Das Layout arbeitet mit `Rect`.
- Die Klickerkennung arbeitet mit `contains_point(...)`.

Das ist eine gute und saubere Arbeitsteilung.

---

## Überlappende Karten: Reihenfolge der Trefferprüfung

Ein sehr typischer Fehler bei GUI-Projekten ist die falsche Reihenfolge der Hit-Tests.

Wenn Karten überlappen, darf nicht einfach in beliebiger Reihenfolge geprüft werden.

Stattdessen gilt normalerweise:

**Geprüft wird von vorne nach hinten.**

Praktisch bedeutet das meist:

**Die zuletzt gezeichnete Karte wird zuerst geprüft.**

Warum?

Weil diese Karte optisch oben liegt und deshalb bei einem Klick normalerweise auch zuerst getroffen werden soll.

Wenn diese Reihenfolge nicht bewusst festgelegt wird, entstehen leicht seltsame Klickfehler.

---

# 2. GUI-Gruppe: Resize bewusst vereinfachen

Beim Thema Resize kann man sehr schnell zu viel wollen.

Darum sollte die Erwartung bewusst klein gehalten werden.

## Sinnvolle Vorgaben

- Es gibt eine **Mindestgröße** des Fensters.
- Unterhalb dieser Mindestgröße muss nicht alles schön aussehen.
- Bei einer Größenänderung wird **das komplette Layout neu berechnet**.
- Es gibt **keine** inkrementellen Einzelverschiebungen.

---

## Was damit gemeint ist

Nicht so:

- „Diese Karte 5 Pixel nach links“
- „jene Karte etwas kleiner“
- „die nächste noch ein wenig nach unten“

Sondern so:

**Aus der aktuellen Fenstergröße wird das gesamte Layout neu berechnet.**

Das ist viel robuster.

---

## Warum vollständige Neuberechnung besser ist

Wenn bei jedem Resize nur einzelne Positionen verschoben werden, sammelt sich leicht unübersichtliche Sonderlogik an.

Dann wird der Code schnell schwer verständlich.

Eine vollständige Neuberechnung hat große Vorteile:

- leichter zu testen
- leichter zu verstehen
- weniger versteckte Abhängigkeiten
- weniger Gefrickel

Eine gute Lehreransage dafür wäre:

> Kein Gefrickel mit alten Positionen.  
> Bei jeder Größenänderung das Layout komplett neu aus den aktuellen Fenstermaßen berechnen.

Das ist vermutlich der wichtigste Hinweis für die GUI-Arbeit.

---

# 3. Netzwerk-Gruppe: die Hub-Schnittstelle früh festlegen

Hier ist eine klare Schnittstelle besonders wichtig.

Wenn die Schnittstelle nicht früh festgelegt wird, verlieren Sie leicht viel Zeit in Grundsatzdiskussionen.

Darum sollte mindestens feststehen:

- Welche Aufrufe es gibt
- Welche Daten hineingehen
- Welche Daten zurückkommen

Noch nicht perfekt, aber eindeutig.

---

## Minimale Idee einer Hub-Schnittstelle

Zum Beispiel so:

```python
hub.start_game(config)
hub.get_view(player_id)
hub.submit_move(player_id, move)
hub.poll_events()
```

Oder nachrichtenartig:

```python
{"type": "start_game", ...}
{"type": "get_view", "player_id": ...}
{"type": "submit_move", "player_id": ..., "card": ...}
```

Beides kann sinnvoll sein.

Wichtig ist nicht, dass die Lösung schon perfekt ist.

Wichtig ist, dass **alle mit derselben Schnittstelle arbeiten**.

---

## Warum diese Vorgabe hilft

Dadurch wird den Beteiligten nicht die Arbeit abgenommen.

Aber es wird verhindert, dass jede Person im Kopf ein anderes System baut.

Gerade am Anfang spart eine klare Schnittstelle sehr viel Zeit.

---

# 4. Thomas: Einfachheit und Framing

Hier sollte der Umfang bewusst sehr klein gehalten werden.

## Wichtigste Vorgabe

Es sollen **keine beliebigen Python-Objekte** serialisiert werden.

Für morgen reicht völlig:

- `dict`
- `list`
- `str`
- `int`
- `bool`
- `None`

und zwar mit:

- `json.dumps(...)`
- `json.loads(...)`

Mehr wird für einen ersten funktionierenden Schritt nicht gebraucht.

---

## Zweiter wichtiger Punkt: Wo endet eine Nachricht?

Bei Netzwerkübertragung reicht „JSON benutzen“ noch nicht ganz aus.

Man braucht zusätzlich eine Regel, woran man erkennt, dass eine Nachricht vollständig ist.

Für morgen ist die einfachste Lösung:

**Eine JSON-Nachricht pro Zeile**

also zum Beispiel:

```python
{"type":"ping","value":123}
```

mit einem Zeilenende dahinter.

Man spricht dabei praktisch von newline-delimited JSON.

---

## Warum diese Begrenzung gut ist

Dadurch wird das Problem klein und gut lösbar.

Ohne diese Begrenzung entsteht leicht unnötige Zusatzarbeit:

- allgemeine Objektserialisierung
- komplizierte Spezialfälle
- unklare Nachrichtenabgrenzung

Darum wäre eine sehr sinnvolle Vorgabe:

> Bitte kein allgemeines Serialisierungssystem bauen.  
> Nur JSON-Nachrichten aus primitiven Typen, eine Nachricht pro Zeile.

Das ist für morgen ein sehr gutes und realistisches Ziel.

---

# 5. Anian und Antonia: den Meilenstein sauber zuschneiden

Hier ist wichtig, das Ziel richtig zu formulieren.

Es geht **noch nicht** darum, schon fast ein vollständiges Netzwerksystem zu bauen.

Es geht zuerst um **Entkopplung**.

## Der eigentliche Kern

Nicht:

> Baut schon fast ein Serversystem.

Sondern:

> Ersetzt den direkten Aufruf  
> **CLI → Engine**  
> durch  
> **CLI → Hub → Engine**

Das ist der eigentliche Meilenstein.

---

## Klare Mini-Regel

Die CLI darf **keine Engine-Methode mehr direkt** aufrufen.

Alles läuft über den Hub.

Das ist eine sehr starke Leitplanke, weil man daran gut überprüfen kann, ob das Ziel erreicht wurde.

---

## Warum dieser Schritt so wichtig ist

Wenn die Entkopplung bereits lokal funktioniert, dann ist später der Schritt zum echten Netzwerk viel einfacher.

Denn dann ist die direkte Abhängigkeit schon entfernt.

Der große Gewinn lautet also:

**Erst Schnittstelle klären, dann Transportweg austauschen.**

---

# 6. Der größte Hebel insgesamt: eine klare Demo pro Gruppe

Schüler arbeiten oft viel besser, wenn von Anfang an klar ist, was am Ende gezeigt werden soll.

Darum sollte jede Gruppe eine sehr konkrete Demo haben.

---

## Demo für die GUI-Gruppe

> Zeigen Sie, dass man mit der Maus auf mehrere Karten klicken kann und die richtige Karte erkannt wird – auch nach einer Fenstergrößenänderung.

Diese Demo passt sehr gut zu den Kernfragen:

- Layout
- Resize
- Treffererkennung
- Überlappung

---

## Demo für Thomas

> Zeigen Sie, dass ein Python-`dict` als JSON gesendet, empfangen und korrekt wieder in ein `dict` zurückverwandelt wird.

Das ist klein, klar und überprüfbar.

---

## Demo für Anian und Antonia

> Zeigen Sie, dass die CLI einen Spielzug über den Hub ausführt, ohne direkt die Engine aufzurufen.

Auch das ist ein sehr guter Meilenstein, weil man daran die Entkopplung direkt erkennen kann.

---

# Fazit

Für morgen ist es besonders wichtig, dass Sie nicht zu viele Dinge gleichzeitig wollen.

Die wichtigsten Leitideen sind:

- saubere Zuständigkeiten
- kleine, klare Schnittstellen
- vollständige Neuberechnung statt Gefrickel
- lieber ein kleiner funktionierender Meilenstein als ein halbfertiges Großprojekt

Wenn diese Grundideen eingehalten werden, ist die Chance deutlich größer, dass am Ende des Unterrichts etwas Funktionierendes vorzeigbar ist.
