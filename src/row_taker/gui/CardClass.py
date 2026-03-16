import os
import sys

import pygame


# -----------------------------
# Card-Klasse
# -----------------------------
class Card:
    """Klasse für eine '6 nimmt!'-Karte für Pygame"""

    CARD_SCALE = 0.15  # Prozent der Fensterbreite

    def __init__(self, number: int):
        self.number = number
        self.points = self.calculate_points()
        self.x = 0
        self.y = 0
        self.image_orig = None
        self.image = None

        # Pfad zum images-Ordner (3 Ordner über gui)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(base_dir, "../../.."))
        self.image_path = os.path.join(project_root, "images", f"{number:03}.png")
        self.image_path = os.path.normpath(self.image_path)

        if os.path.exists(self.image_path):
            self.image_orig = pygame.image.load(self.image_path).convert_alpha()
        else:
            # Wenn das Bild fehlt, Karte ignorieren
            self.image_orig = None

    def calculate_points(self) -> int:
        """Berechnet die Hornochsen-Punkte nach den Spielregeln"""
        n = self.number
        if n == 55:
            return 7
        elif n % 11 == 0:
            return 5
        elif n % 10 == 0:
            return 3
        elif n % 5 == 0:
            return 2
        else:
            return 1

    def scale(self, window_width: int):
        """Skaliert das Bild basierend auf CARD_SCALE"""
        if self.image_orig is None:
            self.image = None
            return

        width = int(window_width * Card.CARD_SCALE)
        height = int(width * 1.5)
        self.image = pygame.transform.scale(self.image_orig, (width, height))

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, (self.x, self.y))


# -----------------------------
# Pygame Setup
# -----------------------------
pygame.init()
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("6 nimmt! Karten")
clock = pygame.time.Clock()

# -----------------------------
# Karten erstellen
# -----------------------------
deck = [Card(i) for i in range(1, 6)]  # Beispiel: Karten 1–5

# Nur Karten mit vorhandenem Bild skalieren
for card in deck:
    card.scale(WIDTH)

# Kartenpositionen: 50 Pixel Abstand
x_pos = 50
for card in deck:
    if card.image:  # nur vorhandene Karten
        card.x = x_pos
        card.y = HEIGHT // 2 - card.image.get_height() // 2
        x_pos += card.image.get_width() + 50

# -----------------------------
# Hauptloop
# -----------------------------
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 120, 0))  # grüner Tisch

    for card in deck:
        card.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()