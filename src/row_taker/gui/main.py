import sys
import os
import pygame


# pygame starten
pygame.init()

# Aktuelle Bildschirmgröße ermitteln
width, height = pygame.display.Info().current_w, pygame.display.Info().current_h
# Fenster erzeugen mit Bildschirmgröße, Taskleiste sichtbar und Fensterrand
screen = pygame.display.set_mode((width, height - 55), pygame.RESIZABLE | pygame.SCALED)
# Uhr für FPS-Steuerung
clock = pygame.time.Clock()
# Fenstertitel
pygame.display.set_caption("Row Taker")

# Programm läuft solange running True ist
running = True

while running:
    # Events, z. B. Fenster schließen
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill("white")  # Hintergrundfarbe Weiß

    pygame.display.flip()  # Bildschirm aktualisieren

    clock.tick(60)  # 60 FPS

pygame.quit()


def main() -> None:
    pass
