from __future__ import annotations

from client_test_support import player_state_for

from row_taker.cli.render import determine_prompt, render_resolution_lines, render_screen
from row_taker.client.core_state import ClientCoreState, PendingAction
from row_taker.client.presentation_events import PresentationCardsRevealed
from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.state import ClientState, enter_game_mode


def _step(event: PresentationCardsRevealed) -> PresentationStep:
    public_state = player_state_for(0).public_state
    return PresentationStep(
        event=event,
        public_state_before=public_state,
        public_state_after=public_state,
    )


def test_pending_presentation_uses_enter_prompt_until_queue_is_empty() -> None:
    state = ClientState(
        core_state=ClientCoreState(
            pending_presentation_steps=(_step(PresentationCardsRevealed(plays=())),)
        ),
    )
    state = enter_game_mode(state, pending_action=PendingAction.CHOOSE_ROW, player_state=player_state_for(0))

    assert determine_prompt(state) == "Weiter mit Enter > "


def test_render_resolution_lines_renders_from_presentation_steps() -> None:
    state = ClientState(
        core_state=ClientCoreState(
            own_player_id="p1",
            presentation_steps=(_step(PresentationCardsRevealed(plays=())),),
        )
    )

    rendered = render_resolution_lines(state)
    assert rendered is not None
    assert "Lokale Auflösung" in rendered


def test_render_screen_renders_lobby_without_current_screen_projection() -> None:
    state = ClientState()

    rendered = render_screen(state)

    assert "Lobby" in rendered
    assert "Menü:" in rendered
