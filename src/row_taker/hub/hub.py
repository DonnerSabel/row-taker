from row_taker.engine.game import setup_game, start_next_round_if_needed
from row_taker.engine.rules import place_card, take_row, target_row_index
from row_taker.engine.state import Card, GameState


class GameHub:
    """
    Verwaltet ein laufendes Row-Taker-Spiel für mehrere Spieler.

      hub.py – GameHub Klasse

      - 3 Zustände: COLLECTING_CARDS → CHOOSING_ROW → zurück, oder GAME_OVER

      - Öffentliche Methoden für Spieler:
        - submit_card(player_index, card_value) – Karte einreichen mit Validierung
        - choose_row(player_index, row_index) – Reihe wählen, wenn nötig
        - get_hand(player_index) – nur die eigenen Karten sehen
        - get_public_state() – Reihen, Scores, Status für alle
      - Interne Auflösungslogik läuft schrittweise ab und pausiert automatisch, wenn ein Spieler eine Reihe wählen muss
      - Kommentare zeigen, wo später Netzwerk-Logik (Timeouts, Bot-Fallback) hinkommt
      - example()-Funktion am Ende zeigt die Benutzung

      Die Klasse ist so gebaut, dass man später einen Flask- oder Socket-Server drumherum bauen kann, der submit_card() und choose_row() bei eingehenden Netzwerknachrichten aufruft.

    Ablauf einer Runde:
    1. Status ist COLLECTING_CARDS: Jeder Spieler ruft submit_card() auf.
    2. Sobald alle eingereicht haben, wird die Runde automatisch aufgelöst.
    3. Falls ein Spieler eine Reihe wählen muss:
       Status wechselt zu CHOOSING_ROW, und der betroffene Spieler
       ruft choose_row() auf.
    4. Danach entweder zurück zu Schritt 1, oder GAME_OVER.
    """

    # Die möglichen Zustände des Hubs
    COLLECTING_CARDS = "collecting_cards"
    CHOOSING_ROW = "choosing_row"
    GAME_OVER = "game_over"

    def __init__(self, player_names: list[str]) -> None:
        """
        Erstellt ein neues Spiel.

        player_names: Liste der Spielernamen (2–6 Spieler).
        """
        self.state: GameState = setup_game(player_names)
        self.status: str = self.COLLECTING_CARDS

        # Welche Karte hat welcher Spieler diese Runde eingereicht?
        # Schlüssel: Spieler-Index, Wert: Karte
        self.submitted_cards: dict[int, Card] = {}

        # Die noch abzuarbeitenden Züge dieser Runde
        # sortiert nach Kartenwert (kleinste zuerst).
        self._pending_moves: list[tuple[int, Card]] = []

        # Wenn ein Spieler eine Reihe wählen muss, steht hier
        # welcher Spieler (Index) und welche Karte er gespielt hat.
        self._row_choice_for: tuple[int, Card] | None = None

        # Beschreibungen der Ereignisse der letzten Runde (für die Anzeige).
        self.last_results: list[str] = []

    # ─── Informationen abfragen ──────────────────────────────────────────────

    def get_hand(self, player_index: int) -> list[int]:
        """
        Gibt die Handkarten eines Spielers zurück (nur Kartenwerte, sortiert).

        Wichtig: Jeder Spieler darf nur seine eigenen Handkarten sehen!
        In einer echten Netzwerkversion würde der Server diese Antwort
        nur an den jeweiligen Spieler schicken.
        """
        return [c.value for c in self.state.players[player_index].hand]

    def get_public_state(self) -> dict:
        """
        Gibt den öffentlichen Spielzustand zurück.

        Das sind Informationen, die alle Spieler sehen dürfen:
        Runde, Reihen (mit Karten und Punkten), Punktestände, Status.
        """
        return {
            "runde": self.state.round_no,
            "reihen": [
                {
                    "karten": [c.value for c in row.cards],
                    "punkte_in_reihe": row.points(),
                }
                for row in self.state.rows
            ],
            "punkte": [{"name": p.name, "strafpunkte": p.score} for p in self.state.players],
            "status": self.status,
        }

    def who_must_choose_row(self) -> str | None:
        """
        Gibt den Namen des Spielers zurück, der gerade eine Reihe
        wählen muss – oder None, wenn niemand wählen muss.
        """
        if self._row_choice_for is None:
            return None
        player_index, _ = self._row_choice_for
        return self.state.players[player_index].name

    # ─── Aktionen der Spieler ────────────────────────────────────────────────

    def submit_card(self, player_index: int, card_value: int) -> tuple[bool, str]:
        """
        Ein Spieler reicht seine gewählte Karte für diese Runde ein.

        Gibt (True, Meldung) bei Erfolg zurück,
        oder (False, Fehlermeldung) wenn etwas nicht stimmt.

        In einer echten Netzwerkversion käme diese Anfrage als Nachricht
        vom Client und würde hier auf dem Server verarbeitet werden.

        Hinweis Netzwerk: Wenn ein Spieler innerhalb von 2 Minuten keine
        Karte einreicht, könnte hier ein Bot die Karte zufällig wählen.
        """
        if self.status != self.COLLECTING_CARDS:
            return False, "Im Moment können keine Karten eingereicht werden."

        if player_index in self.submitted_cards:
            return False, "Du hast diese Runde schon eine Karte eingereicht."

        # Prüfen, ob der Spieler die Karte tatsächlich in der Hand hat.
        player = self.state.players[player_index]
        card = next((c for c in player.hand if c.value == card_value), None)
        if card is None:
            return False, f"Du hast keine Karte mit Wert {card_value} in der Hand."

        self.submitted_cards[player_index] = card

        # Wenn alle Spieler eine Karte eingereicht haben, Runde auflösen.
        if len(self.submitted_cards) == len(self.state.players):
            self._start_round()

        return True, f"Karte {card_value} wurde eingereicht."

    def choose_row(self, player_index: int, row_index: int) -> tuple[bool, str]:
        """
        Ein Spieler wählt eine Reihe aus.

        Das passiert, wenn seine gespielte Karte kleiner war als die letzte
        Karte aller Reihen. Er muss dann eine Reihe nehmen (Strafpunkte!)
        und seine Karte startet dort eine neue Reihe.

        Gibt (True, Meldung) bei Erfolg zurück,
        oder (False, Fehlermeldung) wenn etwas nicht stimmt.

        Hinweis Netzwerk: Wenn der Spieler innerhalb von 2 Minuten keine
        Reihe wählt, könnte ein Bot zufällig eine Reihe wählen.
        """
        if self.status != self.CHOOSING_ROW:
            return False, "Im Moment muss keine Reihe gewählt werden."

        pi, card = self._row_choice_for
        if pi != player_index:
            name = self.state.players[pi].name
            return False, f"Nicht dein Zug – {name} muss die Reihe wählen."

        if not (0 <= row_index < len(self.state.rows)):
            return False, f"Ungültiger Reihen-Index. Bitte 0 bis {len(self.state.rows) - 1} wählen."

        # Reihe nehmen und Karte dort neu starten.
        points, _ = take_row(self.state.rows, row_index)
        self.state.players[pi].score += points
        self.state.rows[row_index].cards = [card]

        name = self.state.players[pi].name
        self.last_results.append(
            f"{name} nimmt Reihe {row_index} ({points} Strafpunkte) "
            f"und startet sie neu mit Karte {card.value}."
        )

        # Diesen Zug als erledigt markieren und weitermachen.
        self._pending_moves.pop(0)
        self._row_choice_for = None
        self._process_next_move()

        return True, f"Reihe {row_index} gewählt ({points} Strafpunkte)."

    # ─── Interne Methoden ────────────────────────────────────────────────────

    def _start_round(self) -> None:
        """
        Wird aufgerufen, sobald alle Spieler ihre Karte eingereicht haben.
        Entfernt die Karten aus den Händen und sortiert die Züge.
        """
        # Karten aus den Händen der Spieler entfernen.
        for pi, card in self.submitted_cards.items():
            self.state.players[pi].hand.remove(card)

        # Züge nach Kartenwert sortieren (Spielregel: kleinste Karte zuerst).
        self.last_results = []
        self._pending_moves = sorted(
            self.submitted_cards.items(),
            key=lambda kv: kv[1].value,
        )
        self.submitted_cards = {}

        self._process_next_move()

    def _process_next_move(self) -> None:
        """
        Arbeitet die offenen Züge der Reihe nach ab.
        Hält an, sobald ein Spieler eine Reihe wählen muss.
        """
        while self._pending_moves:
            player_index, card = self._pending_moves[0]
            row_index = target_row_index(self.state.rows, card)

            if row_index is None:
                # Karte ist kleiner als alle letzten Karten in den Reihen.
                # Der Spieler muss manuell eine Reihe auswählen.
                self._row_choice_for = (player_index, card)
                self.status = self.CHOOSING_ROW
                return  # Warten auf choose_row() vom Spieler.

            # Karte passt in eine Reihe → automatisch platzieren.
            points, taken_cards = place_card(self.state.rows, row_index, card)
            name = self.state.players[player_index].name

            if taken_cards is not None:
                # Die Reihe hatte schon 5 Karten → Spieler nimmt sie (Strafpunkte).
                self.state.players[player_index].score += points
                self.last_results.append(
                    f"{name} füllt Reihe {row_index} auf und nimmt "
                    f"{points} Strafpunkte. Karte {card.value} startet die Reihe neu."
                )
            else:
                self.last_results.append(f"{name} legt Karte {card.value} an Reihe {row_index}.")

            self._pending_moves.pop(0)

        # Alle Züge sind abgearbeitet.
        self._finish_round()

    def _finish_round(self) -> None:
        """
        Beendet die Runde und prüft, ob eine neue Runde gestartet werden kann.
        """
        new_round_started = start_next_round_if_needed(self.state)

        all_hands_empty = all(not p.hand for p in self.state.players)
        if all_hands_empty and not new_round_started:
            # Kein Nachschub mehr möglich → Spiel ist vorbei.
            self.status = self.GAME_OVER
        else:
            self.status = self.COLLECTING_CARDS


# ─── Beispiel-Nutzung ────────────────────────────────────────────────────────


def _print_state(hub: GameHub) -> None:
    state = hub.get_public_state()
    print(f"\n--- Runde {state['runde']} | Status: {state['status']} ---")
    print("Reihen:")
    for i, row in enumerate(state["reihen"]):
        print(f"  [{i}] Karten: {row['karten']}  ({row['punkte_in_reihe']} Punkte)")
    print("Punktestand:")
    for p in state["punkte"]:
        print(f"  {p['name']}: {p['strafpunkte']} Strafpunkte")


def example() -> None:
    """
    Zeigt, wie der GameHub benutzt wird.

    In einer echten Netzwerkversion würden diese Aufrufe von verschiedenen
    Clients über das Netzwerk kommen, statt direkt hier im Code zu stehen.
    """
    hub = GameHub(["Anna", "Ben", "Cara"])

    print("=== Row-Taker Hub – Beispielrunde ===")
    _print_state(hub)

    # Jeder Spieler sieht nur seine eigenen Karten.
    for i, name in enumerate(["Anna", "Ben", "Cara"]):
        print(f"\n{name}s Handkarten: {hub.get_hand(i)}")

    # Jeder Spieler reicht eine Karte ein (hier: jeweils die erste/kleinste).
    for i in range(3):
        hand = hub.get_hand(i)
        card = hand[0]
        ok, message = hub.submit_card(i, card)
        print(f"\nSpieler {i} reicht Karte {card} ein → {message}")

        # Falls nach dem Einreichen eine Reihenwahl nötig ist:
        while hub.status == GameHub.CHOOSING_ROW:
            _print_state(hub)
            chooser = hub.who_must_choose_row()
            chooser_index = next(j for j, p in enumerate(hub.state.players) if p.name == chooser)
            print(f"\n{chooser} muss eine Reihe wählen!")
            ok, message = hub.choose_row(chooser_index, 0)  # wählt Reihe 0
            print(f"→ {message}")

    print("\n=== Ergebnisse der Runde ===")
    for result in hub.last_results:
        print(f"  {result}")

    _print_state(hub)


if __name__ == "__main__":
    example()
