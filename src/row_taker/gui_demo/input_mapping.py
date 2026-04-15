from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass(frozen=True, slots=True)
class GuiDemoInput:
    request_quit: bool = False
    demo_scene_name: str | None = None


NO_INPUT = GuiDemoInput()

_SCENE_KEYS = {
    pygame.K_1: "lobby",
    pygame.K_2: "choose_card",
    pygame.K_3: "choose_row",
    pygame.K_4: "presentation",
}


def map_pygame_event(event: pygame.event.Event) -> GuiDemoInput:
    if event.type == pygame.QUIT:
        return GuiDemoInput(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return GuiDemoInput(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key in _SCENE_KEYS:
        return GuiDemoInput(demo_scene_name=_SCENE_KEYS[event.key])
    return NO_INPUT
