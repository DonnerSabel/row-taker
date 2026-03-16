import pygame
import sys
import os

pygame.init()

# Fenstergröße
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Kartenspiel")
clock = pygame.time.Clock()

# Absoluter Pfad zum Bild
current_dir = os.path.dirname(os.path.abspath(__file__))  # Ordner von Spielwiese.py
card_path = os.path.join(current_dir, "assets", "Ratte.jpg")

# Bild laden
card_image = pygame.image.load(card_path)
card_image = pygame.transform.scale(card_image, (1000, 700))

running = True
while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Hintergrund
    screen.fill((0, 120, 0))

    # Bild zeichnen
    screen.blit(card_image, (0, 0))

    pygame.display.flip()

pygame.quit()
sys.exit()
