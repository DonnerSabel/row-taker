"""
Row-Taker Nachrichten-Protokoll
================================

Schnittstelle zwischen CLI (oder anderem Frontend) und der Engine (GameHub).

Eingehende Nachrichten (Frontend → Engine)
------------------------------------------
  {"type": "start_game",  "players": ["Anna", "Ben", ...]}
  {"type": "get_view",    "player_id": 0}
  {"type": "submit_move", "player_id": 0, "card": 42}
  {"type": "choose_row",  "player_id": 0, "row": 2}

Ausgehende Antworten (Engine → Frontend)
-----------------------------------------
  {"type": "game_started", "players": [...], "round": 1}

  {"type": "view",
   "player_id": 0,
   "hand":   [3, 17, 42, ...],
   "rows":   [{"cards": [...], "points": 3}, ...],
   "scores": [{"name": "Anna", "penalty": 0}, ...],
   "status": "collecting_cards" | "choosing_row" | "game_over",
   "round":  1,
   "need_row_choice": null | {"player_id": 1, "player_name": "Ben", "card": 7}}

  {"type": "accepted",
   "message":         "Karte 42 wurde eingereicht.",
   "status":          "collecting_cards" | "choosing_row" | "game_over",
   "round_results":   ["Anna legt 42 an Reihe 2.", ...] | null,
   "need_row_choice": null | {"player_id": 1, "player_name": "Ben", "card": 7}}

  {"type": "error",      "message": "Fehlerbeschreibung"}
  {"type": "game_over",  "scores": [{"name": "Anna", "penalty": 5}, ...]}
"""
from __future__ import annotations

from typing import Any

from row_taker.hub.hub import GameHub


# ---------------------------------------------------------------------------
# Typ-Aliase für Nachrichten (einfache dicts – serialisierbar zu JSON)
# ---------------------------------------------------------------------------
Message = dict[str, Any]


# ---------------------------------------------------------------------------
# Session – hält den laufenden Hub und leitet Nachrichten weiter
# ---------------------------------------------------------------------------

class Session:
    """
    Verwaltet eine laufende Partie und bietet eine einheitliche
    ``dispatch``-Methode als einzigen Einstiegspunkt.

    Typischer Ablauf::

        session = Session()
        resp = session.dispatch({"type": "start_game", "players": ["Anna", "Ben"]})
        # resp == {"type": "game_started", ...}

        resp = session.dispatch({"type": "get_view", "player_id": 0})
        # resp == {"type": "view", "hand": [...], ...}

        resp = session.dispatch({"type": "submit_move", "player_id": 0, "card": 42})
        # resp == {"type": "accepted", "status": "...", ...}
    """

    def __init__(self) -> None:
        self._hub: GameHub | None = None

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def dispatch(self, message: Message) -> Message:
        """
        Nimmt eine Nachricht entgegen und gibt eine Antwort zurück.

        Alle Validierungsfehler werden als ``{"type": "error", ...}``
        zurückgegeben, damit der Aufrufer nie eine Exception abfangen muss.
        """
        msg_type = message.get("type")

        if msg_type == "start_game":
            return self._handle_start_game(message)

        if self._hub is None:
            return _error("Kein Spiel läuft. Zuerst start_game senden.")

        if msg_type == "get_view":
            return self._handle_get_view(message)
        if msg_type == "submit_move":
            return self._handle_submit_move(message)
        if msg_type == "choose_row":
            return self._handle_choose_row(message)

        return _error(f"Unbekannter Nachrichtentyp: {msg_type!r}")

    # ------------------------------------------------------------------
    # Handler
    # ------------------------------------------------------------------

    def _handle_start_game(self, msg: Message) -> Message:
        players = msg.get("players", [])
        if not isinstance(players, list) or not (2 <= len(players) <= 6):
            return _error("'players' muss eine Liste mit 2–6 Namen sein.")
        if not all(isinstance(n, str) and n.strip() for n in players):
            return _error("Alle Spielernamen müssen nicht-leere Strings sein.")

        self._hub = GameHub([n.strip() for n in players])
        return {
            "type": "game_started",
            "players": [p.name for p in self._hub.state.players],
            "round": self._hub.state.round_no,
        }

    def _handle_get_view(self, msg: Message) -> Message:
        hub = self._hub
        player_id = msg.get("player_id")
        if not isinstance(player_id, int) or not (0 <= player_id < len(hub.state.players)):
            return _error(f"Ungültige player_id: {player_id!r}")

        pub = hub.get_public_state()
        return {
            "type": "view",
            "player_id": player_id,
            "hand": hub.get_hand(player_id),
            "rows": [
                {"cards": r["karten"], "points": r["punkte_in_reihe"]}
                for r in pub["reihen"]
            ],
            "scores": [
                {"name": p["name"], "penalty": p["strafpunkte"]}
                for p in pub["punkte"]
            ],
            "status": pub["status"],
            "round": pub["runde"],
            "need_row_choice": _row_choice_info(hub),
        }

    def _handle_submit_move(self, msg: Message) -> Message:
        hub = self._hub
        player_id = msg.get("player_id")
        card = msg.get("card")

        if not isinstance(player_id, int) or not (0 <= player_id < len(hub.state.players)):
            return _error(f"Ungültige player_id: {player_id!r}")
        if not isinstance(card, int):
            return _error(f"'card' muss eine ganze Zahl sein, nicht {card!r}")

        ok, text = hub.submit_card(player_id, card)
        if not ok:
            return _error(text)

        response: Message = {
            "type": "accepted",
            "message": text,
            "status": hub.status,
            "round_results": hub.last_results if hub.last_results else None,
            "need_row_choice": _row_choice_info(hub),
        }

        if hub.status == GameHub.GAME_OVER:
            pub = hub.get_public_state()
            response["game_over"] = {
                "type": "game_over",
                "scores": [
                    {"name": p["name"], "penalty": p["strafpunkte"]}
                    for p in pub["punkte"]
                ],
            }

        return response

    def _handle_choose_row(self, msg: Message) -> Message:
        hub = self._hub
        player_id = msg.get("player_id")
        row = msg.get("row")

        if not isinstance(player_id, int) or not (0 <= player_id < len(hub.state.players)):
            return _error(f"Ungültige player_id: {player_id!r}")
        if not isinstance(row, int):
            return _error(f"'row' muss eine ganze Zahl sein, nicht {row!r}")

        ok, text = hub.choose_row(player_id, row)
        if not ok:
            return _error(text)

        return {
            "type": "accepted",
            "message": text,
            "status": hub.status,
            "round_results": hub.last_results if hub.last_results else None,
            "need_row_choice": _row_choice_info(hub),
        }


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _error(message: str) -> Message:
    return {"type": "error", "message": message}


def _row_choice_info(hub: GameHub) -> dict | None:
    """Gibt Infos über den Spieler zurück, der eine Reihe wählen muss – oder None."""
    if hub._row_choice_for is None:  # noqa: SLF001
        return None
    player_id, card = hub._row_choice_for  # noqa: SLF001
    return {
        "player_id": player_id,
        "player_name": hub.state.players[player_id].name,
        "card": card.value,
    }
