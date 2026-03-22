# An Anian, Thomas und Antonia – Sinnvolle Meilensteine auf dem Weg zur Netzwerkversion

## Grundgedanke

Bei Netzwerkprojekten ist es wichtig, nicht nur technisch in Einzelproblemen zu denken, sondern in **spielbaren Zwischenständen**.

Das Ziel sollte nicht sein, sofort „alles mit Netzwerk“ zu bauen, sondern mehrere stabile Stufen zu erreichen.

## Meilenstein A – Lokaler Hub, nur CLI, 1 Mensch + Bots

Zunächst noch **kein echtes Netzwerk**.

Trotzdem spricht die CLI schon nicht mehr direkt mit der Engine, sondern nur noch über klar definierte Nachrichten oder Aufrufe einer Hub-Schnittstelle.

### Warum das sinnvoll ist

So kann die Schnittstelle bereits getestet werden, bevor Socket-Programmierung dazukommt.

## Meilenstein B – Bot ebenfalls über dieselbe Schnittstelle

Der Bot soll nicht „irgendwie direkt“ auf die Engine zugreifen, sondern dieselbe Nachrichtenstruktur verwenden wie ein normaler Client.

### Vorteil

Dann gibt es bereits zwei verschiedene Client-Typen auf derselben Schnittstelle:

- Mensch über CLI
- Bot über Nachrichten

Das ist ein starker Test dafür, ob die Schnittstelle sauber entworfen wurde.

## Meilenstein C – JSON-Serialisierung lokal

Jetzt werden die Nachrichten lokal serialisiert und deserialisiert.

Also zum Beispiel:

- Python-Objekt → JSON
- JSON → Python-Objekt

Aber noch ohne echtes TCP.

### Vorteil

Man trennt damit das Nachrichtenformat vom Transport.

## Meilenstein D – TCP auf `localhost`

Erst jetzt kommt der echte Socket dazu.

Alles läuft weiterhin auf einem Rechner, aber die Kommunikation läuft nun real über TCP.

### Vorteil

Viele Fehler können in einer kontrollierten Umgebung gefunden werden, ohne dass mehrere Rechner beteiligt sind.

## Meilenstein E – Externer zweiter Client verbindet sich

Jetzt verbindet sich ein zweiter Client von außen.

Erst an diesem Punkt ist das Spiel tatsächlich netzwerkfähig.

## Warum diese Reihenfolge gut ist

Diese Schritte bauen logisch aufeinander auf:

1. Schnittstelle klären
2. mehrere Client-Arten an dieselbe Schnittstelle hängen
3. Nachrichtenformat stabilisieren
4. echten Transport hinzufügen
5. verteiltes Spiel testen

So entstehen weniger gleichzeitige Fehlerquellen.

## Didaktischer Vorteil

Diese Meilensteine sind nicht nur technisch sinnvoll, sondern auch pädagogisch hilfreich:

- Teilerfolge werden sichtbar
- jede Stufe ist demonstrierbar
- Probleme lassen sich besser eingrenzen
- die Gruppe arbeitet strukturierter

## Fazit

Der wichtigste Gedanke ist:

> Erst dieselbe Sprache festlegen, dann das Kabel dazwischen legen.

Wenn Hub, CLI und Bot bereits lokal über dieselbe Schnittstelle zusammenarbeiten, wird der Schritt zum echten Netzwerk deutlich einfacher.
