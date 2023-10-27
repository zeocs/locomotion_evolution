import random
import math
import copy

import pymunk
from pymunk.vec2d import Vec2d

from genotype import *



class Muscle:

    def __init__(self, creature, muscle_type, node_1, node_2):
        self.creature = creature
        self.muscle_type = muscle_type
        self.node_1 = node_1
        self.node_2 = node_2
        self.is_contracted = False

        self.update_rest_length()
        self.constraint = pymunk.constraints.DampedSpring( \
            node_1.body, node_2.body, (0, 0), (0, 0), \
            self.length, muscle_type.stiffness, muscle_type.damping)
        self.constraint.max_force = muscle_type.max_force

        self.node_1.muscles.append(self)
        self.node_2.muscles.append(self)

    def update_rest_length(self):
        # Needs to be called once initially.
        pos_1 = self.node_1.body.position
        pos_2 = self.node_2.body.position
        self.length = pos_1.get_distance(pos_2)

    def contract(self):
        # Change to shortened/contracted length
        self.is_contracted = True
        self.constraint.rest_length = self.length * self.muscle_type.contract_factor

    def expand(self):
        # Return to normal length
        self.is_contracted = False
        self.constraint.rest_length = self.length


class Node:

    MIN_RADIUS=20
    FRICTION_STICKY=35.0
    FRICTION_NONSTICKY=0.5
    INITIAL_STICKY=False

    def __init__(self, creature, node_type, position):
        # creature (Creature): The creature this node belongs to
        # node_type (NodeType): 
        # position (Vec2d): Where to place the node, absolute position
        self.creature = creature
        self.node_type = node_type
        self.muscles = []

        # Create pymunk body and shape.
        # Put all bodies in the same group so shapes collide.
        mass_radius_factor = 1 + self.node_type.mass / 5
        self.radius = self.MIN_RADIUS * mass_radius_factor
        inertia = pymunk.moment_for_circle(self.node_type.mass, 0, self.radius, (0,0))
        self.body = pymunk.Body(self.node_type.mass, inertia)
        self.body.position = position
        self.shape = pymunk.Circle(self.body, self.radius, (0,0))
        self.shape.filter = pymunk.ShapeFilter(group=1)

        # Set initial stickyness
        self.remember_mass = self.node_type.mass
        self.set_sticky(self.INITIAL_STICKY)

    def set_sticky(self, is_sticky):
        # If the two bodies connected by a constraint are both changed to be static,
        # there is the following error in pymunk:
        # Exception ignored from cffi callback <function SpaceDebugDrawOptions.__init__.<locals>.f5 at 0x7feb48220550>:
        # Traceback (most recent call last):
        #   File "/home/danielg/.local/lib/python3.10/site-packages/pymunk/space_debug_draw_options.py", line 138, in f5
        #     self.draw_dot(size, Vec2d(pos.x, pos.y), self._c(color))
        #   File "/home/danielg/.local/lib/python3.10/site-packages/pymunk/pygame_util.py", line 210, in draw_dot
        #     p = to_pygame(pos, self.surface)
        #   File "/home/danielg/.local/lib/python3.10/site-packages/pymunk/pygame_util.py", line 230, in to_pygame
        #     return round(p[0]), round(p[1])
        # ValueError: cannot convert float NaN to integer
        # As a workaround, a very high mass is used for sticky nodes instead.
        #
        self.is_sticky = is_sticky
        if False:
            # Mode "Mass"
            #STICKY_MASS = 100000
            if is_sticky:
                self.remember_mass = self.body.mass
                self.body.mass = STICKY_MASS
                self.body.velocity *= (self.remember_mass / STICKY_MASS)
            else:
                self.body.mass = self.remember_mass
        else:
            # Mode "Friction"
            if is_sticky:
                self.shape.friction = self.FRICTION_STICKY
            else:
                self.shape.friction = self.FRICTION_NONSTICKY


class Creature:

    MAX_NODES = 50

    NODE_CLASS = Node       # will be overwritten
    MUSCLE_CLASS = Muscle   # will be overwritten

    def __init__(self, space, genome, initial_position):
        # genome (CreatureGenome): The building plan for the creature
        # initial_position (Vec2d): Top left corner of bounding box
        self.space = space
        self.genome = genome
        self.nodes = []     # list positions and node's idx match
        self.muscles = []
        self._build(initial_position)
        self.center_initial = self.get_average_node_position()

    def _build(self, initial_position):
        # Creates the bodies, shapes and constraints for the creature in pymunk

        # Create nodes
        for node_type in self.genome.node_types:
            pos = initial_position + node_type.bb_position
            node = self.NODE_CLASS(self, node_type, pos)
            self.nodes.append(node)
            self.space.add(node.body, node.shape)

        # Create muscles
        for muscle_type in self.genome.matrix.iterate_all_muscles():
            node_1 = self.nodes[muscle_type.node_type_1.idx]
            node_2 = self.nodes[muscle_type.node_type_2.idx]
            muscle = self.MUSCLE_CLASS(self, muscle_type, node_1, node_2)
            self.muscles.append(muscle)
            self.space.add(muscle.constraint)

    def delete(self):
        # Removes the creature's bodies and constraints from space.
        for node in self.nodes:
            self.space.remove(node.body, node.shape)
        for muscle in self.muscles:
            self.space.remove(muscle.constraint)

    def get_average_node_position(self):
        sum_x, sum_y = 0, 0
        for node in self.nodes:
            sum_x += node.body.position.x
            sum_y += node.body.position.y
        count = len(self.nodes)
        return Vec2d(sum_x/count, sum_y/count)

    def get_bounding_box(self):
        x_values = list(map(lambda node: node.body.position.x, self.nodes))
        y_values = list(map(lambda node: node.body.position.y, self.nodes))
        min_x, max_x = min(x_values), max(x_values)
        min_y, max_y = min(y_values), max(y_values)
        return (Vec2d(min_x, min_y), Vec2d(max_x, max_y))

