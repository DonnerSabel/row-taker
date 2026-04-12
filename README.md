# Row-Taker – Unterrichtsprojekt (Python)

**Row-Taker** ist ein Unterrichtsprojekt: ein Kartenspiel mit *„Reihen legen & kassieren“*-Mechanik.
Die Spielidee ist **inspiriert von dem bekannten Kartenspiel „6 nimmt!“ (AMIGO)** – dieses Projekt ist jedoch
**nicht** offiziell, **nicht** verbunden und verwendet **keine** Original-Grafiken, Logos oder Kartentexte.

Ziel ist eine vollständige, lauffähige Implementierung der **Mechanik** mit klarer Trennung zwischen:

- **Engine** – fachliche Zustände und Regeln
- **Hub** – Message-Orchestrierung eines laufenden Spiels
- **Clients** – CLI, Bots und später weitere Frontends

Die aktuelle Referenzoberfläche ist die **CLI**. Netzwerktransport ist architektonisch vorbereitet,
aber noch nicht das aktuelle Arbeitsthema.

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

- **Engine ist fachlich zentral**: `GameState`, `PublicState`, `PlayerState` und `DeltaPublicState` leben in der Engine.
- **Hub ist bewusst schlank**: Der Hub orchestriert Messages und hält keinen zweiten Regelkern.
- **Clients tragen keine Spiellogik**: CLI und Bots verwenden Engine-Funktionen statt eigener Regelrekonstruktion.
- **Darstellung bleibt außerhalb der Engine**: Sortierte Reihenanzeige, Texte, Farben oder GUI-Hit-Tests sind Client-Themen.
- **Tests sichern Regeln und Zuschnitt**: Kernlogik und Message-Fluss sind unit-getestet.

## Repo-Struktur

- `src/row_taker/engine/` – Zustände, Regeln, Übergänge und Projektionen
- `src/row_taker/hub/` – Match-Hub, Match-Konfiguration und Message-Typen
- `src/row_taker/clients/` – CLI-Client und Bot-Clients
- `src/row_taker/cli/` – Terminal-Darstellung und Startpunkt
- `tests/` – Unit-Tests mit pytest
- `docs/` – Architektur, Regeln, Workflow

## Zentrale Datenstrukturen

- `GameState` – autoritativer interner Spielzustand des Hubs
- `PublicState` – öffentlicher Zustand, den der Hub an alle Clients verteilen darf
- `PlayerState` – spielerspezifischer Sichtzustand für genau einen Client
- `DeltaPublicState` – ein einzelner öffentlicher Zustandsübergang während der Trickauflösung

Ein Trick ergibt damit eine Folge von `DeltaPublicState`-Objekten. Clients können denselben Übergang mit der Engine nachvollziehen.

## Lizenz

MIT – siehe `LICENSE`.
