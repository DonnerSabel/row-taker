from __future__ import annotations

import argparse
from pathlib import Path

from row_taker.gui_workbench.app import (
    OFFSCREEN_MOUSE_POS,
    WorkbenchApp,
    save_scenario_frame,
    save_scenario_frames,
    save_timeline_frames,
)
from row_taker.gui_workbench.scenarios import get_scenario, scenario_names, scenarios
from row_taker.gui_workbench.timeline import (
    get_timeline,
    timeline_names,
    timelines,
)


def _parse_size(text: str) -> tuple[int, int]:
    try:
        width_text, height_text = text.lower().split("x", 1)
        width = int(width_text)
        height = int(height_text)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("size must use WIDTHxHEIGHT, for example 1600x900") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("width and height must be positive")
    return width, height


def _parse_point(text: str) -> tuple[int, int]:
    try:
        x_text, y_text = text.split(",", 1)
        return int(x_text), int(y_text)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("mouse must use X,Y, for example 800,700") from exc


def _parse_frames(text: str) -> tuple[int, ...]:
    try:
        frames = tuple(int(item.strip()) for item in text.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("frames must be comma-separated integers") from exc
    if not frames or any(frame < 0 for frame in frames):
        raise argparse.ArgumentTypeError("frames must contain non-negative integers")
    return frames


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m row_taker.gui_workbench",
        description=(
            "Render deterministic scenarios or complete timelines with the "
            "production Row-Taker Pygame GUI."
        ),
    )
    parser.add_argument("scenario", nargs="?", choices=scenario_names())
    parser.add_argument("--timeline", choices=timeline_names(), help="open a complete state timeline")
    parser.add_argument("--step", type=int, default=0, help="timeline step used by --save")
    parser.add_argument("--list", action="store_true", help="list available scenarios")
    parser.add_argument(
        "--list-timelines",
        action="store_true",
        help="list available complete timelines and their steps",
    )
    parser.add_argument("--size", type=_parse_size, help="window/output size as WIDTHxHEIGHT")
    parser.add_argument("--frame", type=int, default=0, help="general animation frame")
    parser.add_argument(
        "--presentation-frame",
        type=int,
        help="presentation animation frame; defaults to --frame",
    )
    parser.add_argument(
        "--mouse",
        type=_parse_point,
        default=OFFSCREEN_MOUSE_POS,
        help="deterministic mouse position X,Y for saved frames",
    )
    parser.add_argument("--save", type=Path, help="render one PNG and exit")
    parser.add_argument("--save-dir", type=Path, help="render a frame series and exit")
    parser.add_argument(
        "--frames",
        type=_parse_frames,
        help="comma-separated frame series; defaults to each state's interesting frames",
    )
    parser.add_argument(
        "--screenshot-dir",
        type=Path,
        default=Path("workbench-screenshots"),
        help="interactive screenshots written by the S key",
    )
    return parser


def _print_scenarios() -> None:
    for scenario in scenarios():
        frames = ",".join(str(frame) for frame in scenario.interesting_frames)
        print(f"{scenario.name:22} {scenario.description} [frames: {frames}]")


def _print_timelines() -> None:
    for timeline in timelines():
        print(f"{timeline.name:22} {timeline.description} [steps: {len(timeline.steps)}]")
        for index, step in enumerate(timeline.steps):
            frames = ",".join(str(frame) for frame in step.interesting_frames)
            print(f"  {index:02d} {step.name:36} {step.description} [frames: {frames}]")


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        _print_scenarios()
    if args.list_timelines:
        _print_timelines()
    if args.list or args.list_timelines:
        return 0

    if args.scenario is not None and args.timeline is not None:
        parser.error("use either a scenario or --timeline, not both")
    if args.scenario is None and args.timeline is None:
        parser.error("a scenario or --timeline is required unless a list option is used")
    if args.frame < 0:
        parser.error("--frame must be non-negative")
    if args.presentation_frame is not None and args.presentation_frame < 0:
        parser.error("--presentation-frame must be non-negative")
    if args.step < 0:
        parser.error("--step must be non-negative")
    if args.save is not None and args.save_dir is not None:
        parser.error("use either --save or --save-dir, not both")
    if args.frames is not None and args.save_dir is None:
        parser.error("--frames requires --save-dir")
    if args.timeline is None and args.step != 0:
        parser.error("--step is only valid with --timeline")

    if args.timeline is not None:
        timeline = get_timeline(args.timeline)
        if args.step >= len(timeline.steps):
            parser.error(
                f"--step must be between 0 and {len(timeline.steps) - 1} "
                f"for timeline {timeline.name!r}"
            )

        if args.save is not None:
            output = save_scenario_frame(
                timeline.steps[args.step],
                args.save,
                size=args.size,
                frame_count=args.frame,
                presentation_frame_count=args.presentation_frame,
                mouse_pos=args.mouse,
            )
            print(output)
            return 0

        if args.save_dir is not None:
            outputs = save_timeline_frames(
                timeline,
                args.save_dir,
                frames=args.frames,
                size=args.size,
                mouse_pos=args.mouse,
            )
            for output in outputs:
                print(output)
            return 0

        return WorkbenchApp(
            timeline=timeline,
            size=args.size,
            frame_count=args.frame,
            presentation_frame_count=args.presentation_frame,
            screenshot_dir=args.screenshot_dir,
        ).run()

    scenario = get_scenario(args.scenario)
    if args.save is not None:
        output = save_scenario_frame(
            scenario,
            args.save,
            size=args.size,
            frame_count=args.frame,
            presentation_frame_count=args.presentation_frame,
            mouse_pos=args.mouse,
        )
        print(output)
        return 0

    if args.save_dir is not None:
        outputs = save_scenario_frames(
            scenario,
            args.save_dir,
            frames=args.frames,
            size=args.size,
            mouse_pos=args.mouse,
        )
        for output in outputs:
            print(output)
        return 0

    return WorkbenchApp(
        scenario,
        size=args.size,
        frame_count=args.frame,
        presentation_frame_count=args.presentation_frame,
        screenshot_dir=args.screenshot_dir,
    ).run()


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
