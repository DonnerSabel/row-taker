import os

import pygame


class Spielfeld:
    """Klasse für ein 6-nimmt!-Spielfeld mit 104 Karten"""

    def __init__(self, image_name: str = "board"):
        # Projektroot finden (3 Ordner hoch von gui/)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(base_dir, "../../.."))
        self.image_path = os.path.join(project_root, "images", f"{image_name}.png")
        self.image_path = os.path.normpath(self.image_path)

        # image wird später dynamisch skaliert
        self.image = None
        self.scaled_image = None
        self.rect = None

    def load_image(self):
        """Laden des Hintergrundbildes ohne Skalierung"""
        try:
            self.image = pygame.image.load(self.image_path)
            self.scaled_image = self.image
            # Rect am oberen linken Eck positionieren
            self.rect = self.scaled_image.get_rect(topleft=(0, 0))
        except FileNotFoundError:
            print(f"Fehler: Bild nicht gefunden: {self.image_path}")
            self.scaled_image = None
            self.rect = None

    def get_image_size(self):
        """Rückgabe der Bildgröße"""
        if self.image:
            return self.image.get_size()
        return (800, 600)  # Fallback Größe

    def draw(self, screen: pygame.Surface):
        """Zeichne das Spielfeld zentriert auf den Screen"""
        if self.scaled_image and self.rect:
            screen.blit(self.scaled_image, self.rect)


def main() -> None:
    # pygame starten
    pygame.init()

    # Spielfeld erstellen
    spielfeld = Spielfeld()
    spielfeld.load_image()

    # Bildgröße ermitteln
    img_width, img_height = spielfeld.get_image_size()

    # Fenster mit Bildgröße erstellen (windowed mode, kein fullscreen)
    screen = pygame.display.set_mode((img_width, img_height))

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

        # Spielfeld zeichnen
        spielfeld.draw(screen)

        pygame.display.flip()  # Bildschirm aktualisieren

        clock.tick(30)  # 30 FPS

    pygame.quit()


if __name__ == "__main__":
    main()
