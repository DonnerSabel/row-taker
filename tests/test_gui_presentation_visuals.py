from __future__ import annotations

from row_taker.gui.presentation_visuals import build_presentation_visuals
from row_taker.gui_workbench.scenarios import get_scenario


def test_cards_revealed_no_longer_uses_legacy_presentation_visuals() -> None:
    visuals = build_presentation_visuals(get_scenario("cards-revealed").state)

    assert visuals.has_event is False
    assert visuals.panel is None
    assert visuals.played_card_values_by_player is None
    assert visuals.focus_card_values == ()


def test_unmigrated_presentation_event_still_exposes_legacy_panel() -> None:
    visuals = build_presentation_visuals(get_scenario("card-placed").state)

    assert visuals.has_event is True
    assert visuals.panel is not None
    assert visuals.panel.headline == visuals.headline
    assert visuals.panel.card_values == visuals.focus_card_values
