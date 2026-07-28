# Contributing (kurz)

- Arbeite immer in einem Feature-Branch: `feat-...`, `fix-...`, `test-...`, `doc-...`
- 1 PR = 1 Ticket / 1 Feature
- `master` ist geschützt: nur Maintainer merged (Rebase and merge)
- Nach Merge: Branch löschen und nicht weiterverwenden
- Vor PR: `tools/run_checks.sh` muss grün sein

Tipp: Nutze `git upmaster` für Solo-Branches (Rebase + force-with-lease).


## Lokale Qualitätsprüfung

```bash
tools/run_checks.sh
python -m build --wheel
python tools/check_wheel.py dist/*.whl
```

`tools/run_checks.sh` prüft Bytecode-Kompilierung, Ruff-Lint, Ruff-Formatierung,
die zentralen typisierten Modulgrenzen mit mypy und die vollständige pytest-Suite. Der Wheel-Smoke-Test installiert das gebaute Paket
außerhalb des Repositorys und prüft CLI, Server, Workbench und paketierte GUI-Ressourcen.
