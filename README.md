# SixNimmt – Unterrichtsprojekt (Python)

Ziel: Eine vollständige, lauffähige Implementierung von **„6 nimmt!“** (Mechanik), zuerst als **CLI**.
Später können **pygame-GUI** und ggf. **Netzwerk** als zusätzliche Frontends folgen.

## Quickstart

Voraussetzung: Python **3.10+**

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e ".[dev]"
pytest -q
python -m sixnimmt.cli
```

## Projektprinzipien (wichtig)

- **Engine ist UI-frei**: keine `print()`/`input()` in `sixnimmt.engine`.
- **Frontends sind austauschbar**: CLI jetzt, pygame/Netzwerk später.
- **Tests** sichern Regeln: Kernlogik ist unit-getestet.

## Repo-Struktur

- `src/sixnimmt/engine/` – Spielregeln & Datenmodelle
- `src/sixnimmt/cli/` – Text-UI (Hotseat)
- `tests/` – Unit-Tests (pytest)
- `.github/workflows/` – CI (Tests laufen automatisch)
- `docs/` – Regeln, Workflow, Branching

## Lizenz / Rechtliches

In diesem Repo werden **keine** originalen Karten-Grafiken/Logos verwendet.
Die Mechanik ist nachgebildet; Thema/Design kann (und sollte) eigenständig sein.
