#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import tempfile
import venv
import zipfile
from pathlib import Path

_CARD_PREFIX = "row_taker/assets/cards/karte_"
_REQUIRED_ASSETS = {
    "row_taker/assets/board.png",
    "row_taker/assets/connect_bg.png",
    "row_taker/assets/titel.png",
}


def _venv_python(venv_dir: Path) -> Path:
    executable = "python.exe" if os.name == "nt" else "python"
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    return venv_dir / scripts_dir / executable


def _host_dependency_roots() -> tuple[Path, ...]:
    roots: set[Path] = set()
    for package_name in ("pygame", "prompt_toolkit"):
        spec = importlib.util.find_spec(package_name)
        if spec is None or spec.origin is None:
            raise RuntimeError(f"wheel smoke test requires installed dependency {package_name!r}")
        roots.add(Path(spec.origin).resolve().parent.parent)
    return tuple(sorted(roots))


def _venv_site_packages(python: Path) -> Path:
    output = subprocess.check_output(
        [
            str(python),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        text=True,
    )
    return Path(output.strip())


def _verify_wheel_contents(wheel_path: Path) -> None:
    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())

    missing = sorted(_REQUIRED_ASSETS - names)
    if missing:
        raise RuntimeError(f"wheel is missing packaged GUI assets: {missing}")

    cards = sorted(
        name for name in names if name.startswith(_CARD_PREFIX) and name.endswith(".png")
    )
    expected_cards = [f"{_CARD_PREFIX}{value:03}.png" for value in range(1, 105)]
    if cards != expected_cards:
        raise RuntimeError(
            "wheel must contain exactly the 104 card images karte_001.png through karte_104.png"
        )


def _verify_installed_wheel(wheel_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="row-taker-wheel-") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        venv_dir = temp_dir / "venv"
        outside_dir = temp_dir / "outside-repository"
        outside_dir.mkdir()

        venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = _venv_python(venv_dir)
        dependency_paths = _venv_site_packages(python) / "row_taker_host_dependencies.pth"
        dependency_paths.write_text(
            "".join(f"{path}\n" for path in _host_dependency_roots()),
            encoding="utf-8",
        )
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-deps", str(wheel_path)],
            check=True,
        )

        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.update(
            {
                "EXPECTED_VENV": str(venv_dir.resolve()),
                "PYGAME_HIDE_SUPPORT_PROMPT": "1",
                "SDL_AUDIODRIVER": "dummy",
                "SDL_VIDEODRIVER": "dummy",
            }
        )
        smoke_code = """
import os
from pathlib import Path

import pygame
import row_taker
from row_taker.gui.assets import DEFAULT_GUI_ASSETS

package_path = Path(row_taker.__file__).resolve()
expected_venv = Path(os.environ["EXPECTED_VENV"]).resolve()
if expected_venv not in package_path.parents:
    raise RuntimeError(f"row_taker imported from {package_path}, not {expected_venv}")

pygame.init()
pygame.display.set_mode((1, 1))
card = DEFAULT_GUI_ASSETS.scaled_card_image(104, 64, 96)
background = DEFAULT_GUI_ASSETS.scaled_connect_background(200, 120)
if card is None or card.get_size() != (64, 96):
    raise RuntimeError("installed wheel could not load card 104")
if background is None or background.get_size() != (200, 120):
    raise RuntimeError("installed wheel could not load the connect background")
pygame.quit()
"""
        subprocess.run(
            [str(python), "-c", smoke_code],
            cwd=outside_dir,
            env=env,
            check=True,
        )
        subprocess.run(
            [str(python), "-m", "row_taker.cli", "--help"],
            cwd=outside_dir,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [str(python), "-m", "row_taker.server", "--help"],
            cwd=outside_dir,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [str(python), "-m", "row_taker.gui_workbench", "--list"],
            cwd=outside_dir,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect and smoke-test an installed Row Taker wheel."
    )
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)

    wheel_path = args.wheel.resolve()
    if not wheel_path.is_file():
        parser.error(f"wheel does not exist: {wheel_path}")

    _verify_wheel_contents(wheel_path)
    _verify_installed_wheel(wheel_path)
    print(f"wheel smoke test passed: {wheel_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
