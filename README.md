# Row-Taker – Unterrichtsprojekt (Python)

**Row-Taker** ist ein Unterrichtsprojekt: ein Kartenspiel mit *„Reihen legen & kassieren“*-Mechanik.
Die Spielidee ist **inspiriert von dem bekannten Kartenspiel „6 nimmt!“ (AMIGO)** – dieses Projekt ist jedoch
**nicht** offiziell, **nicht** verbunden und verwendet **keine** Original-Grafiken, Logos oder Kartentexte.

Ziel ist eine vollständige, lauffähige Implementierung der **Mechanik** mit klarer Trennung zwischen:

- **Engine** – fachliche Zustände und Regeln
- **Hub** – Message-Orchestrierung eines laufenden Spiels
- **Clients** – CLI, Bots und weitere Frontends

Die aktuelle Referenzoberfläche ist die **CLI**. Das Netzwerkspiel ist inzwischen aktiver Projektbestandteil:
Server, CLI-Clients und Bots laufen als getrennte Prozesse und verwenden dasselbe minimale Spielprotokoll.

## Quickstart

Voraussetzung: Python **3.11+**

```bash
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (cmd):
.\.venv\Scripts\activate.bat
# Linux/macOS:
source .venv/bin/activate

python -m pip install -e ".[dev]"
pytest -q
python -m row_taker.server
python -m row_taker.cli
```

## Arbeiten am Projekt (VS Code + Git-Setup)

1) **Git-Projektkonfiguration einbinden** (aus dem Repo-Root):

```bash
git config --local include.path "../_config/gitconfig"
```

2) **VS-Code-Settings übernehmen**
Kopiere die passenden Dateien aus `_config/vscode/` nach `.vscode/`:

- `settings.windows.json` → `.vscode/settings.json` (Windows)
- `settings.linux.json` → `.vscode/settings.json` (Linux)

Optional:
- `_config/vscode/launch.json` → `.vscode/launch.json`
- `_config/vscode/tasks.json` → `.vscode/tasks.json`

3) **Python Interpreter auswählen**
In VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → den Interpreter aus **`.venv`** auswählen.

## Projektprinzipien

- **Engine ist fachlich zentral**: `GameState`, `PublicState` und `PlayerState` leben in der Engine; die Trickauflösung läuft lokal als Resolver / Stepper.
- **Hub ist bewusst schlank**: Der Hub orchestriert Messages und hält keinen zweiten Regelkern.
- **Clients tragen keine eigene Spiellogik**: CLI und Bots verwenden Engine- und Presentation-Strukturen statt lokaler Sonderregeln.
- **Darstellung bleibt außerhalb der Engine**: Sortierte Reihenanzeige, Texte, Farben, GUI-Hit-Tests und Animationen sind Client-Themen.
- **Tests sichern Regeln und Zuschnitt**: Kernlogik, Nachrichtenfluss und Shutdown-Verhalten sind unit-getestet.

## Repo-Struktur

- `src/row_taker/engine/` – Zustände, Regeln, Übergänge und Projektionen
- `src/row_taker/hub/` – Match-Hub, Match-Konfiguration und Message-Typen
- `src/row_taker/clients/` – CLI-Client und Bot-Clients
- `src/row_taker/cli/` – Terminal-Darstellung und Startpunkt
- `tests/` – Unit-Tests mit pytest
- `docs/` – Architektur, Regeln, Workflow

## Zentrale Datenstrukturen

- `GameState` – vollständiger fachlicher Spielzustand in der Engine
- `PublicState` – öffentlicher Zustand des Spiels
- `PlayerState` – spielerspezifischer Sichtzustand für genau einen Client
- `PresentationEvent` – clientseitige Darstellungsereignisse als GUI-neutrale Andockfläche

Die Trickauflösung wird lokal aus den Synchronisationspunkten des Protokolls rekonstruiert. Clients arbeiten dafür mit Resolver-/Stepper-Schritten und leiten daraus `PresentationEvent`-Folgen ab.

## Lizenz

MIT – siehe `LICENSE`.

## Logging und Debugging

Server, CLI-Clients und Bots unterstützen Logging über Python `logging`.

Beispiele:

```bash
python -m row_taker.server --log-level DEBUG --log-file logs/server.log
python -m row_taker.cli --log-level DEBUG --log-file logs/cli-client1.log
python -m row_taker.cli --log-level DEBUG --log-file logs/cli-client2.log
```

Wenn der Server mit `--log-file` läuft, erhalten lokal gestartete Bots automatisch abgeleitete Logdateien, zum Beispiel:

- `logs/server.log`
- `logs/server-bot-1.log`

Typische zusammengehörige Dateien bei einer Fehlersuche sind:

- `server.log`
- `cli-client1.log`
- `cli-client2.log`
- `server-bot-1.log`
