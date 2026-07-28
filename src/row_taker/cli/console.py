from __future__ import annotations

import asyncio
import sys

from prompt_toolkit.application import run_in_terminal
from prompt_toolkit.shortcuts import PromptSession


class InputAborted(Exception):
    pass


class CliConsole:
    def __init__(self) -> None:
        self._session: PromptSession[str] = PromptSession()
        self._screen = ""
        self._prompt: str | None = None
        self._render_lock = asyncio.Lock()
        self._input_active = False

    async def render(self, screen: str, prompt: str | None) -> None:
        async with self._render_lock:
            self._screen = screen
            self._prompt = prompt
            if self._input_active:
                await run_in_terminal(self._write_screen)
            else:
                self._write_screen()

    async def read_line(self) -> str:
        if self._prompt is None:
            raise RuntimeError("read_line() called without active prompt")
        self._input_active = True
        try:
            try:
                value: object = await self._session.prompt_async(self._prompt)
                if not isinstance(value, str):
                    raise TypeError("prompt session returned a non-string value")
                return value
            except KeyboardInterrupt as exc:
                raise InputAborted() from exc
        finally:
            self._input_active = False

    async def close(self) -> None:
        return None

    def _write_screen(self) -> None:
        if sys.stdout.isatty():
            sys.stdout.write("\x1b[2J\x1b[H")
        sys.stdout.write(self._screen)
        if self._screen and not self._screen.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
