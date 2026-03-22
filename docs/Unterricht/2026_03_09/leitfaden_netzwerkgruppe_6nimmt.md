# Leitfaden für die Netzwerkgruppe – Projekt „6 nimmt!“

Dieser Leitfaden richtet sich an die Schüler der Netzwerkgruppe.  
Ihre Aufgabe ist es, die Netzwerkkommunikation für das Spiel „6 nimmt!“ zu entwerfen und zu implementieren.

Die GUI wird von einer anderen Gruppe erstellt.  
Die Netzwerkgruppe entwickelt deshalb zunächst **keine grafische Oberfläche**, sondern arbeitet ausschließlich mit **Konsolenprogrammen**.

Ziel ist es, eine stabile Grundlage zu schaffen, auf die die GUI später aufbauen kann.


## Lernziel

Nach Abschluss dieser Phase sollen Sie:

- eine einfache Client-Server-Architektur verstehen
- ein Nachrichtenprotokoll für das Spiel definieren
- Daten zwischen Client und Server austauschen können
- JSON zur Serialisierung von Nachrichten verwenden
- einen einfachen Testserver und Testclient implementieren können


## Grundidee der Architektur

Für das Projekt verwenden wir eine klassische **Client-Server-Struktur**.

```text
Client A  ----->
                                   >  Server  ----> alle Clients
                 /
Client B  ----->
```

Der **Server** ist die zentrale Instanz des Spiels.

Der Server:

- verwaltet den Spielzustand
- prüft Spielregeln
- verteilt neue Spielzustände an alle Clients

Die Clients:

- senden Aktionen an den Server
- erhalten Spielzustände vom Server


> **Merksatz:** Der Server ist die einzige Instanz, die den vollständigen Spielzustand kennt.


## Transportprotokoll

Sie haben sich zunächst für **UDP** entschieden.

Das ist grundsätzlich möglich, führt aber zu zusätzlichen Problemen:

- Nachrichten können verloren gehen
- Nachrichten können doppelt ankommen
- Nachrichten können in falscher Reihenfolge eintreffen

Zum Vergleich:

TCP bietet bereits:

- garantierte Zustellung
- richtige Reihenfolge
- automatische Wiederholung bei Verlust

> **Hinweis:** Wenn Sie UDP verwenden, müssen Sie einige dieser Probleme selbst lösen.


## Serialisierung der Nachrichten

Nachrichten zwischen Client und Server müssen in ein Format umgewandelt werden, das über das Netzwerk übertragen werden kann.

Wir verwenden dafür **JSON**.

JSON hat mehrere Vorteile:

- leicht lesbar
- in Python direkt unterstützt
- gut für Debugging geeignet


### Beispiel für eine Nachricht

```python
{
    "type": "play_card",
    "card": 23
}
```


Der Client sendet diese Nachricht an den Server, um eine Karte zu spielen.


### Beispiel für eine Serverantwort

```python
{
    "type": "state_update",
    "table": [5, 11, 42, 77],
    "hand": [12, 23, 45]
}
```


Der Server sendet damit den neuen Spielzustand.


> **Merksatz:** Alle Nachrichten werden als JSON-Objekte übertragen.


## Nachrichten des Protokolls

Definieren Sie zunächst ein kleines Set von Nachrichten.

Beispiel für eine erste Version des Protokolls:

| Nachricht | Beschreibung |
|-----------|-------------|
| join | Spieler tritt dem Spiel bei |
| start_game | Spiel beginnt |
| play_card | Spieler legt eine Karte |
| choose_row | Spieler wählt eine Reihe |
| state_update | Server sendet aktuellen Spielzustand |


### Beispiel: join

```python
{
    "type": "join",
    "name": "Alice"
}
```


### Beispiel: play_card

```python
{
    "type": "play_card",
    "card": 23
}
```


### Beispiel: choose_row

```python
{
    "type": "choose_row",
    "row": 2
}
```


## Arbeitsschritte für die Netzwerkgruppe

Arbeiten Sie die folgenden Schritte nacheinander ab.


### Schritt 1 – Protokoll definieren

Schreiben Sie ein Dokument, das folgende Punkte enthält:

- Liste aller Nachrichten
- Beschreibung der Felder
- Beispielnachrichten

Dieses Dokument ist die **Version 1 Ihres Netzwerkprotokolls**.


### Schritt 2 – JSON-Nachrichten erzeugen

Testen Sie zunächst lokal, wie JSON in Python erzeugt und gelesen wird.

```python
import json

msg = {
    "type": "play_card",
    "card": 23
}

data = json.dumps(msg)
print(data)
```


Lesen einer Nachricht:

```python
import json

data = '{"type": "play_card", "card": 23}'
msg = json.loads(data)

print(msg["card"])
```


## Schritt 3 – Einfacher Testserver

Implementieren Sie einen Server, der Nachrichten empfängt und ausgibt.

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 5000))

print("Server gestartet")

while True:
    data, addr = sock.recvfrom(4096)
    print("Nachricht von", addr, data)
```


## Schritt 4 – Einfacher Testclient

Ein Client sendet eine Nachricht an den Server.

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

msg = b"Hallo Server"

sock.sendto(msg, ("127.0.0.1", 5000))
```


Wenn beide Programme laufen, sollte der Server die Nachricht anzeigen.


## Schritt 5 – JSON über das Netzwerk senden

Ersetzen Sie die einfachen Textnachrichten durch JSON.

```python
import socket
import json

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

msg = {
    "type": "join",
    "name": "Alice"
}

data = json.dumps(msg).encode()

sock.sendto(data, ("127.0.0.1", 5000))
```


Der Server kann die Nachricht dann wieder dekodieren.


## Teststrategie

Testen Sie immer in kleinen Schritten:

1. Server starten
2. Client senden lassen
3. Ausgabe kontrollieren

Erst wenn diese Basis stabil funktioniert, erweitern Sie das System.


> **Merksatz:** Entwickeln Sie Netzwerkprogramme immer schrittweise und testen Sie jede Erweiterung sofort.


## Ziel dieser Phase

Am Ende dieser Phase sollen Sie:

- ein dokumentiertes Nachrichtenprotokoll besitzen
- einen funktionierenden Server haben
- mindestens zwei Clients verbinden können
- JSON-Nachrichten zwischen Server und Clients austauschen können


Die GUI-Gruppe kann anschließend diese Netzwerkfunktionen verwenden, um das Spiel grafisch darzustellen.
