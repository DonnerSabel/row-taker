from __future__ import annotations

import pygame

TEXT_PRIMARY = pygame.Color(236, 239, 244)


class PrimitiveDrawer:
    def __init__(self) -> None:
        self._title_font = pygame.font.SysFont(None, 34)
        self._subtitle_font = pygame.font.SysFont(None, 28)
        self._body_font = pygame.font.SysFont(None, 24)
        self._small_font = pygame.font.SysFont(None, 20)
        self._tiny_font = pygame.font.SysFont(None, 17)

    def draw_text(
        self,
        surface: pygame.Surface,
        text: str,
        position: tuple[int, int],
        *,
        role: str = "body",
        color: pygame.Color | None = None,
    ) -> None:
        font = self._font_for_role(role)
        rendered = font.render(text, True, color or TEXT_PRIMARY)
        surface.blit(rendered, position)

    def text_size(self, text: str, *, role: str = "body") -> tuple[int, int]:
        return self._font_for_role(role).size(text)

    def line_height(self, *, role: str = "body") -> int:
        return self._font_for_role(role).get_linesize()

    def draw_wrapped_lines(
        self,
        surface: pygame.Surface,
        lines: list[str],
        rect: pygame.Rect,
        *,
        role: str = "body",
        color: pygame.Color | None = None,
        line_gap: int = 6,
    ) -> int:
        font = self._font_for_role(role)
        y = rect.top
        for line in lines:
            wrapped_lines = self._wrap_line(font, line, rect.width)
            for wrapped_line in wrapped_lines:
                rendered = font.render(wrapped_line, True, color or TEXT_PRIMARY)
                surface.blit(rendered, (rect.left, y))
                y += rendered.get_height() + line_gap
                if y > rect.bottom:
                    return y
        return y

    def measure_wrapped_lines(
        self,
        lines: list[str],
        *,
        max_width: int,
        role: str = "body",
        line_gap: int = 6,
    ) -> int:
        font = self._font_for_role(role)
        height = 0
        first = True
        for line in lines:
            wrapped_lines = self._wrap_line(font, line, max_width)
            for wrapped_line in wrapped_lines:
                if not first:
                    height += line_gap
                height += font.size(wrapped_line)[1]
                first = False
        return height

    def _font_for_role(self, role: str) -> pygame.font.Font:
        if role == "title":
            return self._title_font
        if role == "subtitle":
            return self._subtitle_font
        if role == "small":
            return self._small_font
        if role == "tiny":
            return self._tiny_font
        return self._body_font

    def _wrap_line(self, font: pygame.font.Font, text: str, max_width: int) -> list[str]:
        if text == "":
            return [""]

        words = text.split()
        if not words:
            return [text]

        wrapped_lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                wrapped_lines.append(current)
                current = word
        wrapped_lines.append(current)
        return wrapped_lines
