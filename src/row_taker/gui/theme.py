from __future__ import annotations

from dataclasses import dataclass, field

import pygame


@dataclass(frozen=True, slots=True)
class GuiPalette:
    """Color palette for the polished pygame GUI.

    The demo GUI intentionally keeps its old primitive colors. This palette is
    only used by ``row_taker.gui`` so the nicer client can evolve independently.
    """

    background_top: pygame.Color = field(default_factory=lambda: pygame.Color(17, 24, 39))
    background_bottom: pygame.Color = field(default_factory=lambda: pygame.Color(8, 12, 20))
    board_fallback: pygame.Color = field(default_factory=lambda: pygame.Color(18, 84, 38))

    panel_fill: pygame.Color = field(default_factory=lambda: pygame.Color(24, 31, 44))
    panel_fill_soft: pygame.Color = field(default_factory=lambda: pygame.Color(31, 41, 57))
    panel_fill_strong: pygame.Color = field(default_factory=lambda: pygame.Color(15, 23, 36))
    panel_border: pygame.Color = field(default_factory=lambda: pygame.Color(75, 91, 118))
    panel_border_soft: pygame.Color = field(default_factory=lambda: pygame.Color(255, 255, 255, 45))
    panel_border_active: pygame.Color = field(default_factory=lambda: pygame.Color(125, 190, 255))

    overlay_fill: pygame.Color = field(default_factory=lambda: pygame.Color(0, 0, 0, 120))
    overlay_fill_soft: pygame.Color = field(default_factory=lambda: pygame.Color(0, 0, 0, 35))
    lane_overlay: pygame.Color = field(default_factory=lambda: pygame.Color(0, 0, 0, 22))
    lane_overlay_active: pygame.Color = field(default_factory=lambda: pygame.Color(0, 0, 0, 58))

    text_primary: pygame.Color = field(default_factory=lambda: pygame.Color(236, 239, 244))
    text_muted: pygame.Color = field(default_factory=lambda: pygame.Color(175, 180, 187))

    accent: pygame.Color = field(default_factory=lambda: pygame.Color(102, 163, 255))
    accent_hover: pygame.Color = field(default_factory=lambda: pygame.Color(138, 190, 255))
    gold: pygame.Color = field(default_factory=lambda: pygame.Color(232, 190, 90))
    green: pygame.Color = field(default_factory=lambda: pygame.Color(95, 205, 132))
    danger: pygame.Color = field(default_factory=lambda: pygame.Color(255, 120, 128))

    button_primary: pygame.Color = field(default_factory=lambda: pygame.Color(45, 109, 184))
    button_primary_hover: pygame.Color = field(default_factory=lambda: pygame.Color(68, 139, 220))
    button_success: pygame.Color = field(default_factory=lambda: pygame.Color(46, 145, 86))
    button_success_hover: pygame.Color = field(default_factory=lambda: pygame.Color(61, 174, 106))
    button_danger: pygame.Color = field(default_factory=lambda: pygame.Color(167, 65, 74))
    button_danger_hover: pygame.Color = field(default_factory=lambda: pygame.Color(201, 84, 94))
    button_disabled: pygame.Color = field(default_factory=lambda: pygame.Color(64, 72, 86))

    seat_empty: pygame.Color = field(default_factory=lambda: pygame.Color(36, 45, 60))
    seat_human: pygame.Color = field(default_factory=lambda: pygame.Color(36, 84, 120))
    seat_self: pygame.Color = field(default_factory=lambda: pygame.Color(49, 120, 156))
    seat_bot: pygame.Color = field(default_factory=lambda: pygame.Color(116, 82, 40))
    seat_selected: pygame.Color = field(default_factory=lambda: pygame.Color(78, 110, 148))

    card_fill: pygame.Color = field(default_factory=lambda: pygame.Color(43, 49, 56))
    card_selected: pygame.Color = field(default_factory=lambda: pygame.Color(72, 88, 108))
    card_back_fill: pygame.Color = field(default_factory=lambda: pygame.Color(18, 28, 40, 130))
    card_back_border: pygame.Color = field(default_factory=lambda: pygame.Color(255, 255, 255, 65))

    row_placed: pygame.Color = field(default_factory=lambda: pygame.Color(255, 219, 92))
    row_choice: pygame.Color = field(default_factory=lambda: pygame.Color(120, 196, 255))
    row_taken: pygame.Color = field(default_factory=lambda: pygame.Color(255, 126, 82))
    row_overflow: pygame.Color = field(default_factory=lambda: pygame.Color(255, 82, 82))
    row_neutral: pygame.Color = field(default_factory=lambda: pygame.Color(255, 255, 255, 28))
    taken_badge_fill: pygame.Color = field(default_factory=lambda: pygame.Color(80, 20, 12, 170))
    taken_badge_border: pygame.Color = field(
        default_factory=lambda: pygame.Color(255, 200, 160, 120)
    )


@dataclass(frozen=True, slots=True)
class GuiSpacing:
    panel_radius: int = 18
    large_panel_radius: int = 22
    card_radius: int = 6
    badge_radius: int = 10
    button_radius: int = 12
    overlay_radius: int = 8


@dataclass(frozen=True, slots=True)
class GuiTheme:
    palette: GuiPalette = field(default_factory=GuiPalette)
    spacing: GuiSpacing = field(default_factory=GuiSpacing)


DEFAULT_THEME = GuiTheme()
