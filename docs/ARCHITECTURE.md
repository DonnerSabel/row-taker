# Architektur

## Ziel
- Engine ist unabhängig von UI (CLI/pygame/Netzwerk).
- Später kann ein Netzwerk-Frontend dieselbe Engine verwenden.

## Module
- `sixnimmt.engine.rules` – Regelkern (Zielreihe, Einfügen, Reihen nehmen)
- `sixnimmt.engine.scoring` – Strafpunkte
- `sixnimmt.engine.state` – Dataclasses für Zustand
- `sixnimmt.engine.game` – Ablauf: Setup, Deal, Round-Resolution

## Erweiterbarkeit
- pygame: neues Paket `sixnimmt.pygame_ui` (oder `sixnimmt.ui_pygame`)
- Netzwerk: neues Paket `sixnimmt.net` + Protokoll (JSON Messages)
- Bots/KI: optional `sixnimmt.ai` (z.B. RandomBot, HeuristikBot)
