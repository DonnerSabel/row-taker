# Row-Taker – Unterrichtsprojekt (Python)

**Row-Taker** ist ein Unterrichtsprojekt: ein netzwerkfähiges Kartenspiel mit
*„Reihen legen & kassieren“*-Mechanik. Die Spielidee ist **inspiriert von dem
bekannten Kartenspiel „6 nimmt!“ (AMIGO)** – dieses Projekt ist jedoch **nicht**
offiziell, **nicht** verbunden und verwendet **keine** Original-Grafiken, Logos
oder Kartentexte.

Das Projekt besitzt inzwischen mehrere gleichberechtigte Clients:

- eine Terminaloberfläche,
- eine Pygame-GUI,
- Random-Bots,
- eine deterministische GUI-Workbench für reproduzierbare Szenen und Animationen.

Die gemeinsame Architektur trennt Engine, Match-Hub, Client-Core, Protokoll und
konkrete Frontends.

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
ruff check .
pytest -q
```

Für ein Netzwerkspiel werden Server und Clients in getrennten Terminals gestartet:

```bash
python -m row_taker.server
python -m row_taker.gui
python -m row_taker.cli
```

Die Pygame-Oberflächen können ohne Server in reproduzierbaren Szenen untersucht
werden:

```bash
python -m row_taker.gui_workbench --list
python -m row_taker.gui_workbench card-placed
python -m row_taker.gui_workbench row-taken --save-dir screenshots/row-taken
```

Weitere Bedienung und Architekturregeln stehen in `docs/GUI_WORKBENCH.md`.

## Arbeiten am Projekt (VS Code + Git-Setup)

1. **Git-Projektkonfiguration einbinden** (aus dem Repo-Root):

```bash
git config --local include.path "../_config/gitconfig"
```

2. **VS-Code-Settings übernehmen**

Kopiere die passenden Dateien aus `_config/vscode/` nach `.vscode/`:

- `settings.windows.json` → `.vscode/settings.json` (Windows)
- `settings.linux.json` → `.vscode/settings.json` (Linux)

Optional:

- `_config/vscode/launch.json` → `.vscode/launch.json`
- `_config/vscode/tasks.json` → `.vscode/tasks.json`

3. **Python-Interpreter auswählen**

In VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → den Interpreter
aus **`.venv`** auswählen.

## Projektprinzipien

- **Engine ist fachlich zentral:** `GameState`, `PublicState` und `PlayerState`
  leben in der Engine; die Stichauflösung läuft lokal als Resolver/Stepper.
- **Hub ist bewusst schlank:** Der Hub orchestriert Messages und hält keinen
  zweiten Regelkern.
- **Gemeinsamer Client-Core:** CLI, GUI und Bots verwenden denselben
  `GameClientCore` für Servernachrichten, UI-Aktionen, Revisionen und
  Präsentationsschritte.
- **Darstellung bleibt außerhalb der Engine:** Sortierung, Texte, Farben,
  Hit-Tests und Animationen sind Frontend-Themen.
- **Tests sichern Regeln und Architekturgrenzen:** Kernlogik, Nachrichtenfluss,
  Visual-State-Invarianten und Shutdown-Verhalten sind unit-getestet.

## Repo-Struktur

- `src/row_taker/engine/` – fachliche Zustände, Regeln und Projektionen
- `src/row_taker/hub/` – Match-Hub und Message-Orchestrierung
- `src/row_taker/client/` – Clientzustand, Dispatcher, fachliche Transitionen und Präsentationsqueue
- `src/row_taker/protocol/` – Nachrichten, Codec, Framing und Transport
- `src/row_taker/server/` – Lobby, lokale Bots und Netzwerkserver
- `src/row_taker/cli/` – Terminaldarstellung und CLI-Eingabe
- `src/row_taker/gui/` – Pygame-GUI, Layout, Interaktion und Renderer
- `src/row_taker/bots/` – Bot-Clients
- `src/row_taker/gui_workbench/` – reproduzierbare GUI-Szenen und Timelines
- `tests/` – Unit-, Architektur- und Render-Tests mit pytest
- `docs/` – Architektur, Regeln, Workflow und Unterrichtsmaterial

## Zentrale Datenstrukturen

- `GameState` – vollständiger fachlicher Spielzustand in der Engine
- `PublicState` – öffentlicher Zustand des Spiels
- `PlayerState` – spielerspezifischer Sichtzustand für genau einen Client
- `PresentationStep` – semantischer Präsentationsschritt mit unveränderlichem
  Zustand davor und danach
- `PresentationEvent` – GUI-neutrale Bedeutung eines Präsentationsschritts
- `GameVisualState` – vollständige pygame-unabhängige Projektion der sichtbaren
  Spielansicht, einschließlich Reihen, Spielerkacheln, Hand, Status und Bewegung

Die Stichauflösung wird lokal aus den Synchronisationspunkten des Protokolls
rekonstruiert. Die GUI übersetzt den `ClientState` für jeden vorbereiteten Frame
in einen `GameVisualState`; Pixelkoordinaten und Pygame-Objekte entstehen erst in
der Layout- und Render-Schicht.

## Logging und Debugging

Server, CLI-Clients und Bots unterstützen Logging über Python `logging`.

```bash
python -m row_taker.server --log-level DEBUG --log-file logs/server.log
python -m row_taker.cli --log-level DEBUG --log-file logs/cli-client1.log
python -m row_taker.cli --log-level DEBUG --log-file logs/cli-client2.log
```

Wenn der Server mit `--log-file` läuft, erhalten lokal gestartete Bots automatisch
abgeleitete Logdateien, zum Beispiel:

- `logs/server.log`
- `logs/server-bot-1.log`

Typische zusammengehörige Dateien bei einer Fehlersuche sind:

- `server.log`
- `cli-client1.log`
- `cli-client2.log`
- `server-bot-1.log`

## Lizenz

MIT – siehe `LICENSE`.
