from __future__ import annotations

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from dataclasses import dataclass
from pathlib import Path

import pygame

from row_taker.gui.layout import compute_layout
from row_taker.gui.primitives import PrimitiveDrawer
from row_taker.gui.screens.connect_screen import ConnectFrame
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui.screens.lobby_screen import LobbyFrame
from row_taker.gui.screens.prepared_screen import PreparedScreen
from row_taker.gui_workbench.scenarios import (
    ConnectWorkbenchScenario,
    GameWorkbenchScenario,
    LobbyWorkbenchScenario,
    WorkbenchScenario,
    scenario_category,
)
from row_taker.gui_workbench.timeline import WorkbenchTimeline

WORKBENCH_FPS = 30
OFFSCREEN_MOUSE_POS = (-1, -1)


@dataclass(frozen=True, slots=True)
class RenderedWorkbenchFrame:
    surface: pygame.Surface
    prepared_screen: PreparedScreen



def prepare_headless_pygame() -> None:
    """Prepare SDL for PNG rendering when no graphical session is available."""

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    if not os.environ.get("SDL_VIDEODRIVER") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1), pygame.HIDDEN)



def prepare_scenario_frame(
    scenario: WorkbenchScenario,
    *,
    size: tuple[int, int] | None = None,
    presentation_elapsed_frames: int = 0,
    mouse_pos: tuple[int, int] = OFFSCREEN_MOUSE_POS,
) -> PreparedScreen:
    """Prepare the real production frame for one deterministic scenario."""

    resolved_size = scenario.default_size if size is None else size
    if resolved_size[0] <= 0 or resolved_size[1] <= 0:
        raise ValueError(f"invalid workbench size: {resolved_size!r}")
    layout = compute_layout(*resolved_size)

    match scenario:
        case ConnectWorkbenchScenario():
            return ConnectFrame.from_layout(
                layout=layout,
                connect_form=scenario.connect_form,
                mouse_pos=mouse_pos,
            )
        case LobbyWorkbenchScenario():
            return LobbyFrame.from_layout(
                layout=layout,
                state=scenario.state,
                mouse_pos=mouse_pos,
            )
        case GameWorkbenchScenario():
            return GameFrame.from_layout(
                layout=layout,
                state=scenario.state,
                presentation_elapsed_frames=presentation_elapsed_frames,
                last_action_summary=scenario.last_action_summary,
                mouse_pos=mouse_pos,
            )


def render_scenario_frame(
    scenario: WorkbenchScenario,
    *,
    size: tuple[int, int] | None = None,
    presentation_elapsed_frames: int = 0,
    mouse_pos: tuple[int, int] = OFFSCREEN_MOUSE_POS,
    surface: pygame.Surface | None = None,
    drawer: PrimitiveDrawer | None = None,
) -> RenderedWorkbenchFrame:
    """Render one scenario only through its production prepared frame."""

    resolved_size = scenario.default_size if size is None else size
    if resolved_size[0] <= 0 or resolved_size[1] <= 0:
        raise ValueError(f"invalid workbench size: {resolved_size!r}")

    if surface is None:
        surface = pygame.Surface(resolved_size)
    elif surface.get_size() != resolved_size:
        raise ValueError(
            f"surface size {surface.get_size()!r} does not match requested size {resolved_size!r}"
        )

    prepared_screen = prepare_scenario_frame(
        scenario,
        size=resolved_size,
        presentation_elapsed_frames=presentation_elapsed_frames,
        mouse_pos=mouse_pos,
    )
    prepared_screen.render(surface, drawer=drawer or PrimitiveDrawer())
    return RenderedWorkbenchFrame(
        surface=surface,
        prepared_screen=prepared_screen,
    )



def save_scenario_frame(
    scenario: WorkbenchScenario,
    output_path: Path,
    *,
    size: tuple[int, int] | None = None,
    presentation_elapsed_frames: int = 0,
    mouse_pos: tuple[int, int] = OFFSCREEN_MOUSE_POS,
) -> Path:
    prepare_headless_pygame()
    rendered = render_scenario_frame(
        scenario,
        size=size,
        presentation_elapsed_frames=presentation_elapsed_frames,
        mouse_pos=mouse_pos,
    )
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(rendered.surface, str(output_path))
    return output_path



def save_scenario_frames(
    scenario: WorkbenchScenario,
    output_dir: Path,
    *,
    frames: tuple[int, ...] | None = None,
    size: tuple[int, int] | None = None,
    mouse_pos: tuple[int, int] = OFFSCREEN_MOUSE_POS,
) -> tuple[Path, ...]:
    selected_frames = scenario.interesting_frames if frames is None else frames
    if not selected_frames:
        raise ValueError("at least one frame is required")

    output_dir = output_dir.resolve()
    return tuple(
        save_scenario_frame(
            scenario,
            output_dir / f"{scenario.name}_frame_{frame:03d}.png",
            size=size,
            presentation_elapsed_frames=frame,
            mouse_pos=mouse_pos,
        )
        for frame in selected_frames
    )



def save_timeline_frames(
    timeline: WorkbenchTimeline,
    output_dir: Path,
    *,
    frames: tuple[int, ...] | None = None,
    size: tuple[int, int] | None = None,
    mouse_pos: tuple[int, int] = OFFSCREEN_MOUSE_POS,
) -> tuple[Path, ...]:
    """Render every game timeline step through the production renderer."""

    output_dir = output_dir.resolve()
    outputs: list[Path] = []
    for step_index, scenario in enumerate(timeline.steps):
        selected_frames = scenario.interesting_frames if frames is None else frames
        if not selected_frames:
            raise ValueError("at least one frame is required")
        for frame in selected_frames:
            outputs.append(
                save_scenario_frame(
                    scenario,
                    output_dir
                    / (
                        f"{timeline.name}_step_{step_index:02d}_{scenario.name}_"
                        f"frame_{frame:03d}.png"
                    ),
                    size=timeline.default_size if size is None else size,
                    presentation_elapsed_frames=frame,
                    mouse_pos=mouse_pos,
                )
            )
    return tuple(outputs)


class WorkbenchApp:
    """Interactive resize and timing host around production prepared frames."""

    def __init__(
        self,
        scenario: WorkbenchScenario | None = None,
        *,
        timeline: WorkbenchTimeline | None = None,
        size: tuple[int, int] | None = None,
        presentation_elapsed_frames: int = 0,
        screenshot_dir: Path = Path("workbench-screenshots"),
    ) -> None:
        if (scenario is None) == (timeline is None):
            raise ValueError("provide exactly one scenario or timeline")

        self._timeline = timeline
        self._timeline_step_index = 0
        self._scenarios: tuple[WorkbenchScenario, ...] = (
            (scenario,) if scenario is not None else timeline.steps
        )
        initial_scenario = self._scenarios[0]
        self._initial_size = initial_scenario.default_size if size is None else size
        self._presentation_elapsed_frames = presentation_elapsed_frames
        self._screenshot_dir = screenshot_dir
        self._running = True
        self._auto_advance = False
        self._screenshot_requested = False

    def run(self) -> int:
        pygame.init()
        try:
            pygame.display.set_caption(self._caption())
            screen = pygame.display.set_mode(self._initial_size, pygame.RESIZABLE)
            drawer = PrimitiveDrawer()
            clock = pygame.time.Clock()

            while self._running:
                self._handle_events(screen)
                if not self._running:
                    break

                render_scenario_frame(
                    self.current_scenario,
                    size=screen.get_size(),
                    presentation_elapsed_frames=self._presentation_elapsed_frames,
                    mouse_pos=pygame.mouse.get_pos(),
                    surface=screen,
                    drawer=drawer,
                )
                pygame.display.flip()
                if self._screenshot_requested:
                    self._save_current_frame(screen)
                    self._screenshot_requested = False

                if self._auto_advance:
                    self._presentation_elapsed_frames += 1
                    pygame.display.set_caption(self._caption())
                clock.tick(WORKBENCH_FPS)
            return 0
        finally:
            pygame.quit()

    def _handle_events(self, screen: pygame.Surface) -> None:
        del screen
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                return
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                self._running = False
                return
            if event.key == pygame.K_p:
                self._auto_advance = not self._auto_advance
            elif event.key == pygame.K_RIGHT:
                self._presentation_elapsed_frames += 10 if event.mod & pygame.KMOD_SHIFT else 1
            elif event.key == pygame.K_LEFT:
                step = 10 if event.mod & pygame.KMOD_SHIFT else 1
                self._presentation_elapsed_frames = max(0, self._presentation_elapsed_frames - step)
            elif event.key == pygame.K_HOME:
                self._presentation_elapsed_frames = 0
            elif event.key == pygame.K_PAGEUP:
                self.select_previous_step()
            elif event.key == pygame.K_PAGEDOWN:
                self.select_next_step()
            elif event.key == pygame.K_s:
                self._screenshot_requested = True
            pygame.display.set_caption(self._caption())

    def _save_current_frame(self, screen: pygame.Surface) -> None:
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._screenshot_dir / (
            f"{self.current_scenario.name}_frame_"
            f"{self._presentation_elapsed_frames:03d}.png"
        )
        pygame.image.save(screen, str(output_path))
        print(output_path.resolve())

    @property
    def current_scenario(self) -> WorkbenchScenario:
        return self._scenarios[self._timeline_step_index]

    @property
    def timeline_step_index(self) -> int:
        return self._timeline_step_index

    @property
    def timeline_step_count(self) -> int:
        return len(self._scenarios)

    def select_next_step(self) -> bool:
        return self._select_step(self._timeline_step_index + 1)

    def select_previous_step(self) -> bool:
        return self._select_step(self._timeline_step_index - 1)

    def _select_step(self, index: int) -> bool:
        bounded = min(max(index, 0), len(self._scenarios) - 1)
        if bounded == self._timeline_step_index:
            return False
        self._timeline_step_index = bounded
        self._presentation_elapsed_frames = 0
        self._auto_advance = False
        return True

    def _caption(self) -> str:
        mode = "läuft" if self._auto_advance else "pausiert"
        timeline_part = ""
        if self._timeline is not None:
            timeline_part = (
                f"{self._timeline.name} "
                f"[{self._timeline_step_index + 1}/{len(self._scenarios)}] | "
            )
        return (
            f"Row-Taker GUI-Workbench | {timeline_part}"
            f"{scenario_category(self.current_scenario)}/{self.current_scenario.name} | "
            f"frame={self._presentation_elapsed_frames} | "
            f"{mode} | P Pause, Links/Rechts Frame, Bild auf/ab Zustand, "
            "Home Reset, S Screenshot"
        )
