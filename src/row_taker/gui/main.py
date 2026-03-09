import pygame

# pygame setup
pygame.init()

info = pygame.display.Info()
Width, Height = info.current_w, info.current_h +10

screen = pygame.display.set_mode((Width, Height), pygame.RESIZABLE)
pygame.display.set_caption("Row Taker")
clock = pygame.time.Clock()
running = True

while running:
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:  # Handle window resizing
            Width, Height = event.w, event.h
            screen = pygame.display.set_mode((Width, Height), pygame.RESIZABLE)

    # fill the screen with a color to wipe away anything from last frame
    screen.fill("purple")

    # RENDER YOUR GAME HERE

    # flip() the display to put your work on screen
    pygame.display.flip()

    clock.tick(60)  # limits FPS to 60

pygame.quit()


def main() -> None:
    pass
