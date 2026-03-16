import pygame
import os
from typing import List, Tuple


pygame.init()

# info = pygame.display.Info() //Nur benötigt, wenn get_desktop_sizes()
Width, Height = 1060, 800


# Bilder Ordner
images_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "images")

# Move the Card class definition above its usage


class Card:
    def __init__(
        self, image: pygame.Surface, x: int, y: int, width: int = 150, height: int = 200
    ) -> None:
        self.image = pygame.transform.scale(image, (width, height))
        self.rect = pygame.Rect(x, y, width, height)
        self.enlarged_image = pygame.transform.scale(image, (width + 30, height + 40))

    def draw(self, screen: pygame.Surface, mouse_pos: Tuple[int, int]) -> None:
        if self.rect.collidepoint(mouse_pos):
            screen.blit(self.enlarged_image, (self.rect.x - 15, self.rect.y - 20))
        else:
            screen.blit(self.image, (self.rect.x, self.rect.y))

    @staticmethod
    def load_cards_from_folder(
        folder_path: str, start_x: int = 50, start_y: int = 50, spacing: int = 160
    ) -> List["Card"]:
        """
        Loads card images from a specified folder and creates Card objects for each image.

        :param folder_path: The path to the folder containing card images.
        :param start_x: The x-coordinate where the first card will be placed.
        :param start_y: The y-coordinate where the first card will be placed.
        :param spacing: The horizontal spacing between cards.
        :return: A list of Card objects created from the images in the folder.
        """
        cards = []
        x, y = start_x, start_y
        for filename in os.listdir(folder_path):
            if filename.endswith(".png") or filename.endswith(".jpg"):
                image_path = os.path.join(folder_path, filename)
                image = pygame.image.load(image_path)
                cards.append(Card(image, x, y))
                x += spacing
        return cards


class Bildschirm:
    def __init__(self, width: int, height: int) -> None:
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Row Taker")
        self.clock = pygame.time.Clock()

    def fill(self, color: str) -> None:
        self.screen.fill(color)

    def update(self) -> None:
        pygame.display.flip()

    def tick(self, fps: int) -> None:
        self.clock.tick(fps)


# Reinitialize screen and cards after restoring Bildschirm class
bildschirm = Bildschirm(Width, Height)

# Load all card images
card_images = []
for filename in os.listdir(images_path):
    if filename.endswith(".png") or filename.endswith(".jpg"):
        image_path = os.path.join(images_path, filename)
        card_images.append(pygame.image.load(image_path))

# Create card objects
cards = []
x, y = 50, 50
for image in card_images:
    cards.append(Card(image, x, y))
    x += 160

# initialisieren
bildschirm = Bildschirm(Width, Height)

# Karten laden
cards = Card.load_cards_from_folder(images_path)

# Hauptschleife
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            bildschirm.width, bildschirm.height = event.w, event.h
            bildschirm.screen = pygame.display.set_mode(
                (bildschirm.width, bildschirm.height), pygame.RESIZABLE
            )

    bildschirm.fill("purple")

    # Mausposition
    mouse_pos = pygame.mouse.get_pos()

    # Karten zeichnen
    for card in cards:
        card.draw(bildschirm.screen, mouse_pos)

    bildschirm.update()
    bildschirm.tick(60)

pygame.quit()
