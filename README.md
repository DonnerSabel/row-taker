# Row-Taker – Unterrichtsprojekt (Python)

**Row-Taker** ist ein Unterrichtsprojekt: ein Kartenspiel mit *„Reihen legen & kassieren“*-Mechanik.
Die Spielidee ist **inspiriert von dem bekannten Kartenspiel „6 nimmt!“ (AMIGO)** – dieses Projekt ist jedoch
**nicht** offiziell, **nicht** verbunden und verwendet **keine** Original-Grafiken, Logos oder Kartentexte.

Ziel: Eine vollständige, lauffähige Implementierung der **Mechanik**, zuerst als **CLI**.
Später können **pygame-GUI** und ggf. **Netzwerk** als zusätzliche Frontends folgen.

## Quickstart

Voraussetzung: Python **3.10+**

```bash
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Windows (cmd):
.\.venv\Scripts\activate.bat
# Linux/macOS:
source .venv/bin/activate

pip install -e ".[dev]"
pytest -q
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

Optional (falls du sie nutzen willst):
- `_config/vscode/launch.json` → `.vscode/launch.json`
- `_config/vscode/tasks.json` → `.vscode/tasks.json`

3) **Python Interpreter auswählen**  
In VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → den Interpreter aus **`.venv`** auswählen.

## Projektprinzipien (wichtig)

- **Engine ist UI-frei**: keine `print()`/`input()` in `row_taker.engine`.
- **Frontends sind austauschbar**: CLI jetzt, pygame/Netzwerk später.
- **Tests** sichern Regeln: Kernlogik ist unit-getestet.

## Repo-Struktur

- `src/row_taker/engine/` – Spielregeln & Datenmodelle
- `src/row_taker/cli/` – Text-UI (Hotseat)
- `tests/` – Unit-Tests (pytest)
- `.github/workflows/` – CI (Tests laufen automatisch)
- `docs/` – Regeln, Workflow, Branching

## Lizenz

MIT – siehe `LICENSE`.
