# Workflow

## Regeln

- `master` ist geschützt: nur der Maintainer merged.
- Arbeit immer in einem **Feature-Branch**: `feat-...`, `fix-...`, `test-...`, `doc-...`
- Nach Merge: Branch **löschen** und nicht weiterverwenden.
- Merge-Methode: **Rebase and merge**.

## PR-Größe

- 1 PR = 1 Ticket / 1 Feature.
- Klein halten.
- Architekturumbauten möglichst in klar getrennte Wellen schneiden.

## Vor jedem PR

```bash
tools/run_checks.sh
```

Vor Releases oder Änderungen an Paketierung und Ressourcen zusätzlich:

```bash
python -m build --wheel
python tools/check_wheel.py dist/*.whl
```

Der Standardcheck umfasst Bytecode-Kompilierung, Ruff-Lint, Ruff-Formatprüfung
und die vollständige pytest-Suite.

## Inhaltliche Leitplanken

- Spiellogik gehört in die **Engine**.
- Hub ist **Message-Orchestrator**, kein zweiter Regelkern.
- Clients enthalten **Darstellung und Eingabe**, aber keine eigene Spiellogik.
- Begriffe sauber halten: `client` statt alter `participant`-Denke.
