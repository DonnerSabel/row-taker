from tkinter import OFF


WINDOW_TITLE = "Row Taker"

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700

BACKGROUND_COLOR = (0, 120, 0)

FPS = 60

CARD_SCALE = 0.1
HANDCARD_SCALE = CARD_SCALE / 1.4

CARD_ASPECT_RATIO = 1.5

CARD_GAP = 5
HANDCARD_GAP: float = CARD_GAP * 3.5

OFFSET_HANDCARD_x = 23

# Board play area ratios (relative to board image size)
BOARD_PLAY_AREA_X_RATIO = 0.015  # 2% from left
BOARD_PLAY_AREA_Y_RATIO = 0.07  # 5% from top
BOARD_PLAY_AREA_WIDTH_RATIO = 0.8  # 80% of width
BOARD_PLAY_AREA_HEIGHT_RATIO = 0.85  # 90% of height
