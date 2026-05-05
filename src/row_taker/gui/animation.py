from __future__ import annotations

from dataclasses import dataclass
from math import pi, sin

import pygame


@dataclass(frozen=True, slots=True)
class AnimationClock:
    """Frame-based animation helper for the polished pygame GUI.

    The GUI loop already has a monotonically increasing ``frame_count``. This
    helper keeps tiny visual effects deterministic and local to rendering code:
    no timers, no side effects and no game-state coupling.
    """

    frame_count: int

    def pulse(
        self,
        *,
        period_frames: int = 60,
        low: float = 0.0,
        high: float = 1.0,
    ) -> float:
        """Return a smooth value between ``low`` and ``high``."""

        period = max(1, period_frames)
        phase = (self.frame_count % period) / period
        normalized = (sin(phase * 2.0 * pi) + 1.0) / 2.0
        return low + (high - low) * normalized

    def pulse_alpha(
        self,
        *,
        period_frames: int = 60,
        low: int = 50,
        high: int = 155,
    ) -> int:
        return round(self.pulse(period_frames=period_frames, low=low, high=high))

    def pulse_inflate(
        self,
        *,
        period_frames: int = 60,
        max_pixels: int = 8,
    ) -> int:
        return round(self.pulse(period_frames=period_frames, low=0, high=max_pixels))

    def pulsed_color(
        self,
        base: pygame.Color,
        highlight: pygame.Color,
        *,
        period_frames: int = 60,
        strength_low: float = 0.25,
        strength_high: float = 0.75,
    ) -> pygame.Color:
        strength = self.pulse(
            period_frames=period_frames,
            low=strength_low,
            high=strength_high,
        )
        return base.lerp(highlight, strength)

    def progress(self, *, duration_frames: int = 36) -> float:
        """Return a one-shot progress value from 0.0 to 1.0.

        Unlike ``pulse``, this deliberately does not loop. The polished GUI uses
        it together with an event-local frame counter so a newly visible
        presentation event starts its motion at the beginning.
        """

        duration = max(1, duration_frames)
        return max(0.0, min(1.0, self.frame_count / duration))

    def ease_out_cubic(self, *, duration_frames: int = 36) -> float:
        progress = self.progress(duration_frames=duration_frames)
        return 1.0 - (1.0 - progress) ** 3


def lerp_rect(start: pygame.Rect, end: pygame.Rect, progress: float) -> pygame.Rect:
    """Interpolate between two rectangles.

    The helper keeps card-motion code readable and intentionally works on
    center/size values so cards move and scale smoothly at the same time.
    """

    t = max(0.0, min(1.0, progress))
    width = round(start.width + (end.width - start.width) * t)
    height = round(start.height + (end.height - start.height) * t)
    center_x = round(start.centerx + (end.centerx - start.centerx) * t)
    center_y = round(start.centery + (end.centery - start.centery) * t)
    rect = pygame.Rect(0, 0, max(1, width), max(1, height))
    rect.center = (center_x, center_y)
    return rect
