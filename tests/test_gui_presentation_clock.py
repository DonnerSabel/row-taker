from __future__ import annotations

from row_taker.client.core_state import ClientCoreState
from row_taker.client.presentation_events import PresentationTrickFinished
from row_taker.client.presentation_steps import PresentationStep
from row_taker.client.state import ClientState
from row_taker.gui.app import GuiApp
from row_taker.gui_workbench.scenarios import get_scenario


def _equal_step_pair() -> tuple[PresentationStep, PresentationStep]:
    public_state = get_scenario("choose-card").state.public_state
    assert public_state is not None
    first = PresentationStep(
        event=PresentationTrickFinished(),
        public_state_before=public_state,
        public_state_after=public_state,
    )
    second = PresentationStep(
        event=PresentationTrickFinished(),
        public_state_before=public_state,
        public_state_after=public_state,
    )
    assert first == second
    assert first is not second
    return first, second


def test_presentation_clock_keeps_running_for_same_step_object() -> None:
    step, _ = _equal_step_pair()
    app = GuiApp()
    app._client_state = ClientState(core_state=ClientCoreState(pending_presentation_steps=(step,)))
    app._sync_presentation_clock()
    app._presentation_elapsed_frames = 10

    app._sync_presentation_clock()

    assert app._presentation_step is step
    assert app._presentation_elapsed_frames == 10


def test_presentation_clock_resets_for_equal_but_distinct_steps() -> None:
    first, second = _equal_step_pair()
    app = GuiApp()
    app._client_state = ClientState(core_state=ClientCoreState(pending_presentation_steps=(first,)))
    app._sync_presentation_clock()
    app._presentation_elapsed_frames = 10

    app._client_state = ClientState(
        core_state=ClientCoreState(pending_presentation_steps=(second,))
    )
    app._sync_presentation_clock()

    assert app._presentation_step is second
    assert app._presentation_elapsed_frames == 0


def test_tick_advances_only_while_a_presentation_step_is_active() -> None:
    step, _ = _equal_step_pair()
    app = GuiApp()

    class ClockStub:
        def tick(self, fps: int) -> None:
            assert fps > 0

    app._clock = ClockStub()  # type: ignore[assignment]
    app._tick()
    assert app._presentation_elapsed_frames == 0

    app._presentation_step = step
    app._tick()
    assert app._presentation_elapsed_frames == 1
