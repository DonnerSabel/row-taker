# Workflow (Rebase + PR)

## Regeln
- `master` ist geschützt: nur der Maintainer merged.
- Arbeit immer in einem **Feature-Branch**: `feat-...`, `fix-...`, `test-...`, `doc-...`
- Nach Merge: Branch **löschen** und nicht weiterverwenden.
- Merge-Methode: **Rebase and merge** (keine Squash-Merges).

## PR-Größe
- 1 PR = 1 Ticket / 1 Feature.
- Klein halten (idealerweise < 200 Zeilen Änderung).

## CI
- Tests laufen automatisch auf jedem Push & PR.
- PR wird nur gemerged, wenn CI grün ist.
