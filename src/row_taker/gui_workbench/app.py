from __future__ import annotations

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from dataclasses import dataclass
from pathlib import Path

import pygame

from row_taker.gui.screens.game_screen import GameFrame
from row_taker.gui_common.layout import compute_layout
from row_taker.gui_common.primitives import PrimitiveDrawer
from row_taker.gui_workbench.scenarios import WorkbenchScenario

WORKBENCH_FPS = 30
OFFSCREEN_MOUSE_POS = (-1, -1)


@dataclass(frozen=True, slots=True)
class RenderedWorkbenchFrame:
    surface: pygame.Surface
    game_frame: GameFrame


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


def render_scenario_frame(
    scenario: WorkbenchScenario,
    *,
    size: tuple[int, int] | None = None,
    frame_count: int = 0,
    presentation_frame_count: int | None = None,
    mouse_pos: tuple[int, int] = OFFSCREEN_MOUSE_POS,
    surface: pygame.Surface | None = None,
    drawer: PrimitiveDrawer | None = None,
) -> RenderedWorkbenchFrame:
    """Render one workbench frame through the production ``GameFrame`` only."""

    resolved_size = scenario.default_size if size is None else size
    if resolved_size[0] <= 0 or resolved_size[1] <= 0:
        raise ValueError(f"invalid workbench size: {resolved_size!r}")

    if surface is None:
        surface = pygame.Surface(resolved_size)
    elif surface.get_size() != resolved_size:
        raise ValueError(
            f"surface size {surface.get_size()!r} does not match requested size {resolved_size!r}"
        )

    layout = compute_layout(*resolved_size)
    game_frame = GameFrame.from_layout(
        layout=layout,
        state=scenario.state,
        frame_count=frame_count,
        presentation_frame_count=(
            frame_count
            if presentation_frame_count is None
            else presentation_frame_count
        ),
        last_action_summary=scenario.last_action_summary,
        mouse_pos=mouse_pos,
    )
    game_frame.render(surface, drawer=drawer or PrimitiveDrawer())
    return RenderedWorkbenchFrame(surface=surface, game_frame=game_frame)


def save_scenario_frame(
    scenario: WorkbenchScenario,
    output_path: Path,
    *,
    size: tuple[int, int] | None = None,
    frame_count: int = 0,
    presentation_frame_count: int | None = None,
    mouse_pos: tuple[int, int] = OFFSCREEN_MOUSE_POS,
) -> Path:
    prepare_headless_pygame()
    rendered = render_scenario_frame(
        scenario,
        size=size,
        frame_count=frame_count,
        presentation_frame_count=presentation_frame_count,
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
            frame_count=frame,
            presentation_frame_count=frame,
            mouse_pos=mouse_pos,
        )
        for frame in selected_frames
    )


class WorkbenchApp:
    """Interactive timing and resize host around the production game renderer."""

    def __init__(
        self,
        scenario: WorkbenchScenario,
        *,
        size: tuple[int, int] | None = None,
        frame_count: int = 0,
        presentation_frame_count: int | None = None,
        screenshot_dir: Path = Path("workbench-screenshots"),
    ) -> None:
        self._scenario = scenario
        self._initial_size = scenario.default_size if size is None else size
        self._frame_count = frame_count
        self._presentation_frame_count = (
            frame_count
            if presentation_frame_count is None
            else presentation_frame_count
        )
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

                mouse_pos = pygame.mouse.get_pos()
                render_scenario_frame(
                    self._scenario,
                    size=screen.get_size(),
                    frame_count=self._frame_count,
                    presentation_frame_count=self._presentation_frame_count,
                    mouse_pos=mouse_pos,
                    surface=screen,
                    drawer=drawer,
                )
                pygame.display.flip()
                if self._screenshot_requested:
                    self._save_current_frame(screen)
                    self._screenshot_requested = False

                if self._auto_advance:
                    self._frame_count += 1
                    self._presentation_frame_count += 1
                    pygame.display.set_caption(self._caption())
                clock.tick(WORKBENCH_FPS)
            return 0
        finally:
            pygame.quit()

    def _handle_events(self, screen: pygame.Surface) -> None:
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
                self._presentation_frame_count += 10 if event.mod & pygame.KMOD_SHIFT else 1
            elif event.key == pygame.K_LEFT:
                step = 10 if event.mod & pygame.KMOD_SHIFT else 1
                self._presentation_frame_count = max(0, self._presentation_frame_count - step)
            elif event.key == pygame.K_UP:
                self._frame_count += 10 if event.mod & pygame.KMOD_SHIFT else 1
            elif event.key == pygame.K_DOWN:
                step = 10 if event.mod & pygame.KMOD_SHIFT else 1
                self._frame_count = max(0, self._frame_count - step)
            elif event.key == pygame.K_HOME:
                self._frame_count = 0
                self._presentation_frame_count = 0
            elif event.key == pygame.K_s:
                self._screenshot_requested = True
            pygame.display.set_caption(self._caption())

    def _save_current_frame(self, screen: pygame.Surface) -> None:
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._screenshot_dir / (
            f"{self._scenario.name}_frame_{self._frame_count:03d}_"
            f"presentation_{self._presentation_frame_count:03d}.png"
        )
        pygame.image.save(screen, str(output_path))
        print(output_path.resolve())

    def _caption(self) -> str:
        mode = "läuft" if self._auto_advance else "pausiert"
        return (
            f"Row-Taker GUI-Workbench | {self._scenario.name} | "
            f"frame={self._frame_count} presentation={self._presentation_frame_count} | "
            f"{mode} | P Pause, Pfeile Schritt, Home Reset, S Screenshot"
        )
