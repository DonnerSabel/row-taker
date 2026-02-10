# Architektur

## Ziel
- Engine ist unabhängig von UI (CLI/pygame/Netzwerk).
- Später kann ein Netzwerk-Frontend dieselbe Engine verwenden.

## Module
- `row_taker.engine.rules` – Regelkern (Zielreihe, Einfügen, Reihen nehmen)
- `row_taker.engine.scoring` – Strafpunkte
- `row_taker.engine.state` – Dataclasses für Zustand
- `row_taker.engine.game` – Ablauf: Setup, Deal, Round-Resolution

## Erweiterbarkeit
- pygame: neues Paket `row_taker.pygame_ui` (oder `row_taker.ui_pygame`)
- Netzwerk: neues Paket `row_taker.net` + Protokoll (JSON Messages)
- Bots/KI: optional `row_taker.ai` (z.B. RandomBot, HeuristikBot)
