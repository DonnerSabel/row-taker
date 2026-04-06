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
pytest -q
```

Optional zusätzlich:

```bash
tools/run_checks.sh
```

## Inhaltliche Leitplanken

- Spiellogik gehört in die **Engine**.
- Hub ist **Message-Orchestrator**, kein zweiter Regelkern.
- Clients enthalten **Darstellung und Eingabe**, aber keine eigene Spiellogik.
- Begriffe sauber halten: `client` statt alter `participant`-Denke.
