# An Antonia – Welche API-Funktionen für die erste Netzwerkversion wirklich nötig sind

## Grundidee

Für die erste Version einer Netzwerk-API ist es sinnvoll, zwischen **Pflicht** und **Optional** zu unterscheiden.

Damit vermeiden Sie zwei typische Probleme:

- Die erste Version wird zu groß.
- Wichtige Kernfunktionen gehen zwischen Nebenthemen unter.

## Pflicht: Verbindung und Lobby

### 1. `hello`
Der Client meldet sich und nennt seine Protokollversion.

Das ist wichtig, damit spätere Änderungen am Protokoll möglich bleiben.

### 2. Spielername setzen
Zum Beispiel über `set_player_name` oder direkt beim Join.

### 3. `create_lobby`
Ein Host eröffnet eine Lobby.

### 4. `join_lobby`
Ein weiterer Client tritt mit Code oder ID bei.

### 5. `leave_lobby`
Ein sauberer Austritt ist wichtig, damit der Server aufräumen kann.

### 6. Lobby-Zustand übertragen
Entweder per Anfrage `get_lobby_state` oder besser als Server-Event wie `lobby_state` bzw. `lobby_updated`.

Alle Clients sollen sehen können:

- wer in der Lobby ist
- wer bereit ist
- wer Host ist

### 7. `set_ready`
Vor Spielbeginn fast immer notwendig.

### 8. `start_game`
Entweder durch den Host oder automatisch, wenn alle bereit sind.

## Pflicht: Spielphase

### 9. Spielzustand an den Client übertragen
Der Client muss immer wissen, was aktuell gilt.

Typische Inhalte:

- öffentliche Reihen
- Punktestände
- aktuelle Phase
- welche Aktion vom Spieler erwartet wird

Ein guter Nachrichtentyp dafür ist `game_state`.

### 10. `play_card`
Das ist die zentrale Aktion eines Spielers.

Als Nutzdaten ist eine stabile Kennung besser als eine reine Anzeigezahl, also eher `card_id` als nur ein sichtbarer Textwert.

### 11. `choose_row`
Wenn eine gespielte Karte kleiner als alle Reihenenden ist, muss der Spieler eine Reihe wählen.

Diese Nachricht ist für das Spiel unverzichtbar.

### 12. Fehler zurückmelden
Nicht unbedingt als eigene API-Funktion, aber als Nachrichtentyp wie `error`.

Beispiele:

- Sie sind nicht am Zug.
- Diese Karte haben Sie nicht auf der Hand.
- Die gewählte Reihe ist ungültig.

### 13. Rundenauflösung übertragen
Zum Beispiel als `round_resolved` oder als Folge einzelner Ereignisse.

Die Clients müssen verstehen können:

- wer welche Karte gespielt hat
- wer welche Reihe genommen hat
- wie sich Reihen und Punkte verändert haben

### 14. `game_over`
Das Spielende mit Endstand und Sieger gehört in jede erste vollständige Version.

## Optional, aber sinnvoll

Diese Punkte sind nützlich, aber für eine erste lauffähige Version nicht zwingend:

- `reconnect` / `resume_session`
- `ping` / `pong`
- Chat
- Zuschauer-Modus
- Host-Rechte wie `kick_player`
- Bots hinzufügen oder entfernen
- Lobby-Einstellungen ändern
- vollständigen Snapshot anfordern

## Vorschlag für eine minimale erste API

### Client → Server

- `hello`
- `create_lobby`
- `join_lobby`
- `leave_lobby`
- `set_ready`
- `start_game`
- `play_card`
- `choose_row`

### Server → Client

- `welcome`
- `lobby_state`
- `game_started`
- `game_state`
- `row_choice_required`
- `round_resolved`
- `error`
- `game_over`

Das reicht bereits für eine erste funktionierende Version.

## Beispielhafter Ablauf

### Vor dem Spiel

1. Client sendet `hello`
2. Server antwortet `welcome`
3. Host sendet `create_lobby`
4. andere Clients senden `join_lobby`
5. alle senden `set_ready`
6. Host sendet `start_game`
7. Server sendet `game_started` und `game_state`

### Während des Spiels

1. Spieler sendet `play_card`
2. falls nötig sendet der Server `row_choice_required`
3. Spieler sendet `choose_row`
4. Server löst die Runde auf
5. Server sendet `round_resolved`
6. Server sendet den neuen `game_state`

### Ende

Server sendet `game_over`.

## Fazit

Für die erste Version sollten Sie klein, klar und vollständig planen.

Wichtiger als viele Zusatzfunktionen ist zunächst eine API, die genau einen vollständigen Spielablauf sauber abbilden kann.
