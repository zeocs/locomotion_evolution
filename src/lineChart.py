
from datetime import datetime, timedelta
import pygame
import math


class LineChart:

    POINT_X_SPACING = 5

    YAXIS_WIDTH = 100
    YAXIS_MARGIN = 15   # space between yaxis and chart

    YAXIS_TICK_HEIGHT = 50    # height of font plus spacing to next tick
    YAXIS_TICKMARK_LENGTH = 10
    YAXIS_LINE_COLOR = (50, 50, 50)

    PADDING_RIGHT = 15   # don't draw all the way to the right, keep some empty space

    LINE_COLOR = (255, 255, 255)    # also used for yaxis and text


    def __init__(self, screen, font, topleft_pos, size):
        """
        screen: pygame screen object
        topleft_pos, size: tuples of two ints (x, y)
        """
        self.screen = screen
        self.font = font
        self.topleft_pos = topleft_pos
        self.size = size

        self._global_min = None
        self._global_max = None

        # Each element is a tuple, consisting of:
        # 1. a pygame color, 2. a list of numbers
        self._datasets = []

        # Determine region bounding boxes (exclusive spacing between them)
        self.yaxis_rect = pygame.Rect( \
            self.topleft_pos[0], \
            self.topleft_pos[1], \
            self.YAXIS_WIDTH, \
            self.size[1])
        self.chart_rect = pygame.Rect( \
            self.yaxis_rect.right + self.YAXIS_MARGIN, \
            self.topleft_pos[1], \
            self.size[0] - self.yaxis_rect.width - self.YAXIS_MARGIN, \
            self.size[1])
        #print(self.size)
        #print(self.yaxis_rect)
        #print(self.chart_rect)


    def _amount_to_y(self, amount):
        diff = self._global_max - self._global_min
        factor = (float(amount) - self._global_min) / diff
        y = self.chart_rect.bottom - self.chart_rect.height * factor
        #assert(y >= self.chart_rect.top and y <= self.chart_rect.bottom)
        return y

    def set_datasets(self, datasets):
        self._datasets = datasets

    def render(self):
        # Determine how many points are really drawable given the chart width
        nb_drawable_points = int((self.chart_rect.width - self.PADDING_RIGHT) / self.POINT_X_SPACING)
        #print(self.chart_rect.width, self.PADDING_RIGHT, nb_drawable_points)
        #print(self.chart_rect.width, self.PADDING_RIGHT, self.POINT_X_SPACING)

        # Get the points that are drawable for each dataset
        drawable_points = []
        for color, points in self._datasets:
            #print(points, nb_drawable_points, points[-nb_drawable_points:])
            dps = [p for p in points[-nb_drawable_points:] if p is not None]
            if len(dps) < 2:
                continue # Too few points to draw this dataset
            drawable_points.append((color, dps))

        # Determine factors for vertical scaling
        self._global_max, self._global_min = None, None
        for dps_color, dps in drawable_points:
            if self._global_max is None or max(dps) > self._global_max:
                self._global_max = float(max(dps))
            if self._global_min is None or min(dps) < self._global_min:
                self._global_min = float(min(dps))

        # Draw y axis
        pygame.draw.line(self.screen, self.LINE_COLOR, \
            (self.yaxis_rect.right, self.yaxis_rect.top), \
            (self.yaxis_rect.right, self.yaxis_rect.bottom))
        if self._global_max is None or self._global_min is None \
            or self._global_max == self._global_min:
            self._global_max = 500
            self._global_min = 0
        #print("self._global_max", self._global_max, "self._global_min", self._global_min)

        # Draw y axis tickmarks, ticklines and label texts
        amount_diff = self._global_max - self._global_min
        max_num_ticks = self.size[1] // self.YAXIS_TICK_HEIGHT
        tick_amount = max(math.floor(amount_diff // max_num_ticks), 1)
        tick_amount_digits = int(math.log10(tick_amount))+1     # number of digits of tick_amount
        factor = (10 ** (tick_amount_digits-1))
        tick_amount = int(math.ceil(tick_amount / factor) * factor)
        lowest_tick_amount = int((self._global_min // tick_amount) * tick_amount)
        highest_tick_amount = int((self._global_max // tick_amount) * tick_amount)
        #print(lowest_tick_amount, highest_tick_amount, tick_amount, factor, tick_amount_digits)
        for amount in range(lowest_tick_amount, highest_tick_amount + tick_amount, tick_amount):
            #if amount < self._global_min:
            #    continue        # hacky fix for some problem... TODO
            tick_y = self._amount_to_y(amount)
            # Draw tick mark
            pygame.draw.line(self.screen, self.LINE_COLOR, \
                (self.yaxis_rect.right - self.YAXIS_TICKMARK_LENGTH, tick_y), (self.yaxis_rect.right, tick_y))
            # Draw tick level inside chart
            pygame.draw.line(self.screen, self.YAXIS_LINE_COLOR, \
                (self.chart_rect.left + 1, tick_y), (self.chart_rect.right, tick_y))
            amount_text, amount_text_rect = self.font.render("{:,}".format(amount), self.LINE_COLOR)
            amount_text_pos = ( \
                self.yaxis_rect.right - amount_text_rect.width - 20, \
                tick_y - (amount_text_rect.height / 2))
            self.screen.blit(amount_text, amount_text_pos, None)

        # Draw graph
        for dps_color, dps in drawable_points:
            cur_x, last_x, last_dp = None, None, None
            coords = list(zip(
                [self.chart_rect.left + dps_idx * self.POINT_X_SPACING for dps_idx in range(len(dps))],
                [self._amount_to_y(dps) for dps in dps]
            ))
            pygame.draw.lines(self.screen, dps_color, False, coords)
