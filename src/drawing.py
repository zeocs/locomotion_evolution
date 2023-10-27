import pygame
import math

from timer import TimerNode

from genotype import *


class Drawing:

    COLOR_NODE_STICKY = (0,128,255)
    COLOR_NODE_NONSTICKY = (0,0,192)
    RADIUS_NODE = 10

    COLOR_MUSCLE = (128,128,128)

    COLOR_GROUND = (255,255,255)

    DRAW_TIMERS = True


    def __init__(self, ui):
        # ui (Graphics): 
        self.ui = ui

    def draw_creature(self, creature, show_specs=False):
        for node in creature.nodes:
            pos = self.ui.draw_options.transform @ node.body.position
            radius = int(node.radius * self.ui.scaling)
            color = self.COLOR_NODE_STICKY if node.is_sticky else self.COLOR_NODE_NONSTICKY
            if self.DRAW_TIMERS and isinstance(node, TimerNode):
                arc_rect = pygame.Rect(pos.x-radius, pos.y-radius, radius*2, radius*2)
                pygame.draw.arc(self.ui.game.screen, self.COLOR_NODE_NONSTICKY, arc_rect, \
                    -node.timer.timer_type.true_from, -node.timer.timer_type.false_from)
                pygame.draw.arc(self.ui.game.screen, self.COLOR_NODE_STICKY, arc_rect, \
                    -node.timer.timer_type.false_from, -node.timer.timer_type.true_from)
                timer_now_pos = (
                    pos.x + math.cos(node.timer.value) * radius,
                    pos.y + math.sin(node.timer.value) * radius
                )
                pygame.draw.line(self.ui.game.screen, color, pos, timer_now_pos, 2)
                pygame.draw.circle(self.ui.game.screen, color, pos, int(radius/2))
                if show_specs:
                    self.ui._draw_text("{:.2f}, {:.2f}, {:.2f}".format(
                        node.timer.value, node.timer.timer_type.true_from, node.timer.timer_type.false_from), pos, True)
            else:
                pygame.draw.circle(self.ui.game.screen, color, pos, radius)

        for muscle in creature.muscles:
            pos_1 = self.ui.draw_options.transform @ muscle.constraint.a.position
            pos_2 = self.ui.draw_options.transform @ muscle.constraint.b.position
            pygame.draw.line(self.ui.game.screen, self.COLOR_MUSCLE, pos_1, pos_2)
            if show_specs:
                pos_mid = (pos_1 + pos_2) / 2
                pos_line1 = pos_mid - Vec2d(0, -12)
                pos_line2 = pos_mid - Vec2d(0, 12)
                damping_percent = int((muscle.muscle_type.damping - MuscleType.DAMPING_MIN)
                    / (MuscleType.DAMPING_MAX - MuscleType.DAMPING_MIN) * 100)
                stiffness_percent = int((muscle.muscle_type.stiffness - MuscleType.STIFFNESS_MIN)
                    / (MuscleType.STIFFNESS_MAX - MuscleType.STIFFNESS_MIN) * 100)
                contract_factor_percent = int((muscle.muscle_type.contract_factor - MuscleType.CONTRACT_FACTOR_MIN)
                    / (MuscleType.CONTRACT_FACTOR_MAX - MuscleType.CONTRACT_FACTOR_MIN) * 100)
                max_force_percent = int((muscle.muscle_type.max_force - MuscleType.MAX_FORCE_MIN)
                    / (MuscleType.MAX_FORCE_MAX - MuscleType.MAX_FORCE_MIN) * 100)
                self.ui._draw_text("dp={}% st={}%".format(damping_percent, stiffness_percent),
                    pos_line1, True)
                self.ui._draw_text("cf={}% mf={}%".format(contract_factor_percent, max_force_percent),
                    pos_line2, True)

    def draw_genome(self, genome, bb_topleft):
        for node_type in genome.node_types:
            pos = self.ui.draw_options.transform @ (bb_topleft + node_type.bb_position)
            radius = int(self.RADIUS_NODE * self.ui.scaling)
            color = self.COLOR_NODE_STICKY
            pygame.draw.circle(self.ui.game.screen, color, pos, radius)
        for muscle_type in genome.muscle_matrix.iterate_all_muscles():
            pos_1 = self.ui.draw_options.transform @ (bb_topleft + muscle_type.node_type_1.bb_position)
            pos_2 = self.ui.draw_options.transform @ (bb_topleft + muscle_type.node_type_2.bb_position)
            pygame.draw.line(self.ui.game.screen, self.COLOR_MUSCLE, pos_1, pos_2)

    def draw_ground(self, segments):
        # segments (pymunk.Segment[]): The segments to draw, must be contiguous,
        #   i.e., the next must start where the previous one ended
        # Is faster than drawing lines separately, I hope?
        points = [self.ui.draw_options.transform @ segments[0].a]
        for segment in segments:
            points.append(self.ui.draw_options.transform @ segment.b)
        pygame.draw.lines(self.ui.game.screen, self.COLOR_GROUND, False, points)

