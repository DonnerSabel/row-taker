import pygame
import os
import sys  # <-- unbedingt hinzufügen

class Card:
    """
    Klasse für eine '6 nimmt!'-Karte für Pygame
    """

    def __init__(self, number: int, x: int = 0, y: int = 0, image_folder: str = "karten"):
        self.number = number
        self.points = self.calculate_points()
        self.x = x
        self.y = y
        self.image_path = os.path.join(image_folder, f"karte_{number}.png")
        self.image = self.load_image()

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

    def load_image(self) -> pygame.Surface:
        """Lädt das Bild als Pygame Surface"""
        if os.path.exists(self.image_path):
            image = pygame.image.load(self.image_path).convert_alpha()  # transparentes PNG
            return image
        else:
            # Platzhalter-Image, falls Bild fehlt
            image = pygame.Surface((200, 300), pygame.SRCALPHA)
            image.fill((255, 255, 255, 255))
            font = pygame.font.Font(None, 60)
            text = font.render(str(self.number), True, (0, 0, 0))
            image.blit(text, (50, 120))
            return image

    def draw(self, surface: pygame.Surface):
        """Zeichnet die Karte auf die gegebene Pygame-Oberfläche"""
        surface.blit(self.image, (self.x, self.y))

    def set_position(self, x: int, y: int):
        """Setzt die Kartenkoordinaten"""
        self.x = x
        self.y = y

    def __repr__(self):
        return f"<Card {self.number}, {self.points} Hornochsen, pos=({self.x},{self.y})>"


# -------------------------------
# Pygame Setup
# -------------------------------
pygame.init()
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("6 nimmt! Karten Test")
clock = pygame.time.Clock()

# Karten erstellen
deck = [Card(n) for n in range(1, 6)]  # die ersten 5 Karten
for i, card in enumerate(deck):
    card.set_position(50 + i*210, 200)  # nebeneinander platzieren

# -------------------------------
# Haupt-Loop
# -------------------------------
running = True
while running:
    screen.fill((0, 120, 0))  # grüner Tisch

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Karten zeichnen
    for card in deck:
        card.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()