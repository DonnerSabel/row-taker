from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True, slots=True)
class GuiDemoInput:
    request_quit: bool = False


NO_INPUT = GuiDemoInput()


def map_pygame_event(event: pygame.event.Event) -> GuiDemoInput:
    if event.type == pygame.QUIT:
        return GuiDemoInput(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return GuiDemoInput(request_quit=True)
    return NO_INPUT
