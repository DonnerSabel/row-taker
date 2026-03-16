import pygame
import sys

pygame.init()

# Fenster
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Klickbares Quadrat")

clock = pygame.time.Clock()

# Quadrat in der Mitte
square_size = 100
square_color = (0, 0, 255)  # Blau
square_rect = pygame.Rect(
    (WIDTH - square_size) // 2, (HEIGHT - square_size) // 2, square_size, square_size
)

running = True
while running:
    clock.tick(120)

    # Events prüfen
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Klick prüfen
        if event.type == pygame.MOUSEBUTTONDOWN:
            if square_rect.collidepoint(event.pos):
                # Farbe wechseln
                if square_color == (0, 0, 255):
                    square_color = (255, 0, 0)  # Rot
                else:
                    square_color = (0, 0, 255)  # Blau

    # Hintergrund
    screen.fill((0, 120, 0))  # Grün wie Kartentisch

    # Quadrat zeichnen
    pygame.draw.rect(screen, square_color, square_rect)

    # Bildschirm aktualisieren
    pygame.display.flip()

pygame.quit()
sys.exit()
