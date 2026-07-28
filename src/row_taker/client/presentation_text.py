from __future__ import annotations

from row_taker.client.presentation_events import (
    PresentationCardPlaced,
    PresentationCardsRevealed,
    PresentationEvent,
    PresentationGameFinished,
    PresentationOverflowResolved,
    PresentationRoundFinished,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
    PresentationTrickFinished,
)


def format_presentation_event(event: PresentationEvent) -> str:
    """Return a compact frontend-neutral summary of a presentation event."""

    if isinstance(event, PresentationCardsRevealed):
        cards = ", ".join(f"{play.player_name}:{play.card_value}" for play in event.plays)
        return f"Karten aufgedeckt -> {cards}"
    if isinstance(event, PresentationCardPlaced):
        return (
            f"Karte angelegt -> {event.player_name} legt {event.card_value} an Reihe {event.row_id}"
        )
    if isinstance(event, PresentationRowChoiceRequired):
        return f"Reihenauswahl nötig -> {event.player_name} mit {event.card_value}"
    if isinstance(event, PresentationRowChosen):
        return f"Reihe gewählt -> {event.player_name} nimmt {event.row_id}"
    if isinstance(event, PresentationRowTaken):
        return f"Reihe genommen -> {event.player_name} erhielt {event.bullheads} Hornochsen"
    if isinstance(event, PresentationOverflowResolved):
        return f"Überlauf aufgelöst -> {event.player_name} erhielt {event.bullheads} Hornochsen"
    if isinstance(event, PresentationTrickFinished):
        return "Stich beendet"
    if isinstance(event, PresentationRoundFinished):
        return "Runde beendet"
    if isinstance(event, PresentationGameFinished):
        return "Spiel beendet"
    return event.__class__.__name__
