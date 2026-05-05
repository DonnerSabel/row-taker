from __future__ import annotations

import pygame

from row_taker.gui_common.layout import PANEL_PADDING

PANEL_FILL = pygame.Color(32, 36, 41)
PANEL_BORDER = pygame.Color(135, 145, 156)
WINDOW_BACKGROUND = pygame.Color(20, 22, 25)
TEXT_PRIMARY = pygame.Color(236, 239, 244)
TEXT_MUTED = pygame.Color(175, 180, 187)
ACCENT = pygame.Color(102, 163, 255)
CARD_FILL = pygame.Color(43, 49, 56)
CARD_SELECTED = pygame.Color(72, 88, 108)


class PrimitiveDrawer:
    def __init__(self) -> None:
        self._title_font = pygame.font.SysFont(None, 34)
        self._subtitle_font = pygame.font.SysFont(None, 28)
        self._body_font = pygame.font.SysFont(None, 24)
        self._small_font = pygame.font.SysFont(None, 20)
        self._tiny_font = pygame.font.SysFont(None, 17)

    def draw_panel(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        title: str | None = None,
    ) -> pygame.Rect:
        pygame.draw.rect(surface, PANEL_FILL, rect)
        pygame.draw.rect(surface, PANEL_BORDER, rect, width=1)

        content_rect = rect.inflate(-2 * PANEL_PADDING, -2 * PANEL_PADDING)
        if title is not None:
            self.draw_text(surface, title, (content_rect.left, content_rect.top), role="title")
            content_rect = pygame.Rect(
                content_rect.left,
                content_rect.top + 28,
                content_rect.width,
                max(0, content_rect.height - 28),
            )
        return content_rect

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

    def draw_key_value(
        self,
        surface: pygame.Surface,
        key: str,
        value: str,
        position: tuple[int, int],
    ) -> None:
        self.draw_text(surface, key, position, role="small", color=TEXT_MUTED)
        self.draw_text(surface, value, (position[0] + 120, position[1]), role="body")

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

    def draw_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        value: int,
        bullheads: int,
        selected: bool = False,
    ) -> None:
        fill = CARD_SELECTED if selected else CARD_FILL
        pygame.draw.rect(surface, fill, rect)
        pygame.draw.rect(surface, PANEL_BORDER if not selected else ACCENT, rect, width=1)

        self.draw_text(surface, str(value), (rect.left + 8, rect.top + 6), role="body")
        self.draw_text(surface, f"{bullheads} bh", (rect.left + 8, rect.top + 30), role="small", color=TEXT_MUTED)

    def draw_badge(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        text: str,
        active: bool = False,
    ) -> None:
        pygame.draw.rect(surface, CARD_SELECTED if active else CARD_FILL, rect)
        pygame.draw.rect(surface, ACCENT if active else PANEL_BORDER, rect, width=1)
        self.draw_text(surface, text, (rect.left + 8, rect.top + 6), role="small")

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
