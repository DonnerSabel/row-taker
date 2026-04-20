import pygame


class PlayerIcon:
    """Ein skalierbares Spieler-Icon: Kreis + Spielernummer + Hervorhebung."""

    def __init__(
        self,
        number: int,
        radius: int = 40,
        color=(255, 255, 255),
        text_color=(0, 0, 0),
        highlight_color=(255, 215, 0)  # Gold
    ):
        self.number = number
        self.radius = radius
        self.color = color
        self.text_color = text_color
        self.highlight_color = highlight_color

        self.is_active = False  # <--- NEU

        self.x = 0
        self.y = 0

        self.image = None
        self.rect = None

        self._render()

    def _render(self):
        """Erzeugt das Icon als Surface."""
        diameter = self.radius * 2

        # Extra Platz für Hervorhebung
        padding = int(self.radius * 0.25)
        total_size = diameter + padding * 2

        self.image = pygame.Surface((total_size, total_size), pygame.SRCALPHA)

        center = (total_size // 2, total_size // 2)

        # Falls aktiv → Highlight-Ring zeichnen
        if self.is_active:
            pygame.draw.circle(
                self.image,
                self.highlight_color,
                center,
                self.radius + padding // 2
            )

        # Normaler Kreis
        pygame.draw.circle(self.image, self.color, center, self.radius)

        # Text rendern
        font_size = int(self.radius * 1.2)
        font = pygame.font.SysFont(None, font_size, bold=True)
        text = font.render(str(self.number), True, self.text_color)

        text_rect = text.get_rect(center=center)
        self.image.blit(text, text_rect)

        # Rect aktualisieren
        self.rect = self.image.get_rect(topleft=(self.x, self.y))

    def set_position(self, x: int, y: int):
        self.x = x
        self.y = y
        if self.rect:
            self.rect.topleft = (x, y)

    def scale(self, new_radius: int):
        """Skaliert das Icon neu."""
        self.radius = new_radius
        self._render()

    def set_active(self, active: bool):
        """Aktiviert oder deaktiviert die Hervorhebung."""
        self.is_active = active
        self._render()

    def draw(self, surface: pygame.Surface):
        if self.image:
            surface.blit(self.image, (self.x, self.y))

def create_player_icons(player_count: int, start_x: int, start_y: int, spacing: int, radius: int = 40):
    """Erzeugt und positioniert Spieler-Icons untereinander."""
    icons = []

    for i in range(1, player_count + 1):
        icon = PlayerIcon(i, radius=radius)
        icon.set_position(start_x, start_y + (i - 1) * (radius * 2 + spacing))
        icons.append(icon)

    return icons


def draw_player_icons(surface, icons):
    """Zeichnet alle Icons."""
    for icon in icons:
        icon.draw(surface)


