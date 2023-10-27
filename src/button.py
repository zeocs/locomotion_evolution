import pygame


class Button:

    TEXT_COLOR=(255,255,255)
    BORDER_COLOR=(192,192,192)
    BORDER_WIDTH=1
    BORDER_RADIUS=5

    def __init__(self, ui, x, y, text, callback, toggle=False):
        # ui (UI): Reference to the UI instance
        # x (int): 
        # y (int):
        # text (string): 
        # callback (function): Invoked when button is pressed. For toggle buttons,
        #   True is given as argument if button is pressed, False when not pressed
        #   No argument is given for normal buttons.
        # toggle (bool): Whether this is a toggling button (True) or not.
        self.ui = ui
        self.x = x
        self.y = y
        self.callback = callback
        self.toggle = toggle
        self.set_text(text)

    def set_text(self, text):
        width, height = self.font.size(text)
        self.text = text
        self.text_surface = self.font.render(text, (255,255,255))
        self.text_rect = Rect(x, y, width, height)

    def render(self):
        ui.screen.blit(self.text_surface, (self.x, self.y), None)
        pygame.draw.rect(self.ui.screen, self.text_rect, self.BORDER_COLOR, \
            self.BORDER_WIDTH, self.BORDER_RADIUS)
