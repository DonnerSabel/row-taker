# An Thomas – Warum die Aufteilung in Transport und Codec sinnvoll ist und weshalb TCP hier besser passt als UDP

## Sinnvolle Aufgabenverteilung

Eine sehr gute technische Aufteilung ist:

- JSON serialisieren
- JSON deserialisieren
- Nachrichtenrahmen über TCP festlegen
- senden und empfangen
- nach `type` dispatchen

Diese Trennung ist sinnvoll, weil sie zwei Ebenen auseinanderhält:

### Inhaltsebene
Welche Nachricht meinen wir fachlich?

Zum Beispiel:

- `play_card`
- `choose_row`
- `game_state`

### Transportebene
Wie kommt diese Nachricht zuverlässig von A nach B?

## Warum diese Trennung wichtig ist

Wenn Inhalt und Transport vermischt werden, wird alles unübersichtlich:

- Spiellogik hängt direkt an Socket-Details
- Fehler sind schwerer zu lokalisieren
- Tests werden komplizierter
- ein späterer Wechsel des Transports wird unnötig schwer

Mit einer sauberen Trennung kann man zum Beispiel lokale Tests mit denselben Nachrichtentypen machen, noch bevor echte Netzwerkkommunikation aktiv ist.

## Ganz wichtiger Punkt: TCP statt UDP

Für ein rundenbasiertes Kartenspiel würde ich sehr klar sagen:

> TCP ist hier fast sicher die bessere Wahl.

## Warum TCP hier gut passt

Bei Row-Taker / 6 nimmt sind diese Eigenschaften wichtig:

- Reihenfolge der Nachrichten ist wichtig
- Zuverlässigkeit ist wichtig
- die Datenmengen sind klein
- es gibt keine harten Echtzeitanforderungen wie bei einem Shooter

Genau dafür ist TCP sehr gut geeignet.

## Was bei UDP zusätzlich gelöst werden müsste

Wenn Sie stattdessen UDP verwenden, müssen Sie viele Probleme selbst lösen:

- Paketverlust
- falsche Reihenfolge
- doppelte Pakete
- Wiederholung von Nachrichten
- Bestätigungen
- eigene Zuverlässigkeitsschicht

Das bedeutet sehr viel Zusatzarbeit, obwohl das Spiel davon kaum profitiert.

## Warum UDP hier wenig Nutzen bringt

UDP ist interessant, wenn minimale Latenz wichtiger ist als Zuverlässigkeit, zum Beispiel bei bestimmten Echtzeitanwendungen.

Bei einem rundenbasierten Kartenspiel ist aber eine korrekte, vollständige und geordnete Übertragung viel wichtiger als das letzte bisschen Geschwindigkeit.

## Praktischer Vorteil von TCP

Mit TCP kann sich die Gruppe zunächst auf die eigentliche Aufgabe konzentrieren:

- gutes Nachrichtenformat
- saubere API
- klare Zustandsübergänge
- robustes Dispatching

Statt Zeit in eine selbst gebaute Zuverlässigkeitsschicht zu investieren.

## Fazit

Die geplante Aufteilung in Transport und Codec ist sehr sinnvoll.

Für dieses Projekt ist TCP die vernünftige Standardwahl, weil es genau die Eigenschaften mitbringt, die ein rundenbasiertes Mehrspielerspiel benötigt.
