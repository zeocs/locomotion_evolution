
import pymunk
import math
import random
from phenotype import Muscle, Node, Creature
from genotype import Genome
from timer import TimerNode, TimerMuscle, TimerNodeType, TimerMuscleType


class Simulation:
    """
    An instance simulates a set of creatures, specified via a list of genomes,
    for a set amount of time.
    """

    # Higher gives more physics accuracy, but slower, default is 10
    ITERATIONS = 10

    # Smaller helps reduce "missed collisions", default is 1/50.0
    TIMESTEMP_DELTA=1/100.0

    # Air friction: Factor applied to bodies velocity per second
    DAMPING = 0.05

    # Gravity
    GRAVITY = (0, 1500)

    GROUND_LEVEL = 1000
    WALL_HEIGHT = 550
    SPAWN_AREA_LENGTH = 1100

    # Slope in degrees
    GROUND_SLOPE_DEV_MIN = -30
    GROUND_SLOPE_DEV_MAX = 30
    GROUND_SLOPE_INCREASE = 0.04
    GROUND_SEGMENT_MIN_LENGTH = 30
    GROUND_SEGMENT_MAX_LENGTH = 40
    GROUND_SEGMENTS_COUNT = 700
    GROUND_FRICTION=8.0

    def __init__(self, generation, max_ticks):
        Creature.NODE_CLASS = TimerNode
        Creature.MUSCLE_CLASS = TimerMuscle

        # generation (Generation): Among other things, contains genomes for creatures
        # max_ticks (int): For how many ticks to simulate the creature before
        #   measuring its fitness and terminating the simulation

        # General properties
        self.generation = generation
        self.max_ticks = max_ticks
        self.cur_ticks = 0  # number of timesteps simulated so far

        # The simulated world
        self.creatures = []
        self.segments = []

        # Each element is a tuple (fitness, creature).
        # Sorted descendingly, best to worst fitness.
        # Set by self.evaluate().
        self.ranked_creatures = []

        # Create space
        self.space = pymunk.Space()
        self.space.iterations = self.ITERATIONS
        self.space.damping = self.DAMPING
        self.space.gravity = self.GRAVITY

        # Create wall on left
        wall = pymunk.Segment(self.space.static_body, \
            (-self.SPAWN_AREA_LENGTH, self.GROUND_LEVEL-self.WALL_HEIGHT), \
            (-self.SPAWN_AREA_LENGTH, self.GROUND_LEVEL), 1.0)
        wall.friction = self.GROUND_FRICTION
        self.space.add(wall)
        self.segments.append(wall)

        # Create ground
        x, y = -self.SPAWN_AREA_LENGTH, self.GROUND_LEVEL
        for i in range(0, self.GROUND_SEGMENTS_COUNT):
            if i == 0:
                # Create a start area with no slope
                length = self.SPAWN_AREA_LENGTH
                angle = 0
            elif i == self.GROUND_SEGMENTS_COUNT-1:
                # End piece that allows creatures to slide down ("ultimate win")
                length = 300
                angle = 15/8 * math.pi
            else:
                length = random.randint( \
                    self.GROUND_SEGMENT_MIN_LENGTH, self.GROUND_SEGMENT_MAX_LENGTH)
                angle = math.radians(int(i * self.GROUND_SLOPE_INCREASE) \
                    + random.uniform(self.GROUND_SLOPE_DEV_MIN, self.GROUND_SLOPE_DEV_MAX))
            end_x = x + math.cos(angle) * length
            end_y = y - math.sin(angle) * length
            end_y = min(end_y, self.GROUND_LEVEL)
            segment = pymunk.Segment(self.space.static_body, (x, y), (end_x, end_y), 1.0)
            segment.friction = self.GROUND_FRICTION
            self.space.add(segment)
            self.segments.append(segment)
            x, y = end_x, end_y

        # Create the creatures
        x = -self.SPAWN_AREA_LENGTH/2 - Genome.BB_WIDTH/2
        y = self.GROUND_LEVEL - Genome.BB_HEIGHT - 20
        for genome in self.generation.genomes:
            creature = Creature(self.space, genome, (x, y))
            self.creatures.append(creature)

    def get_total_nodes(self):
        # Get total number of nodes in the simulation
        count = 0
        for creature in self.creatures:
            count += len(creature.nodes)
        return count

    def get_fitness(self, creature):
        # Get the fitness of the specified creature
        any_node_not_on_ground = False
        for node in creature.nodes:
            if node.body.position.y < self.GROUND_LEVEL - node.radius - 15:
                any_node_not_on_ground = True
                break

        if any_node_not_on_ground:
            center = creature.get_average_node_position()
            dist = max(0, abs(center.x - creature.center_initial.x))
            perf = dist
        else:
            perf = 0

        return perf

    def evaluate(self):
        # Updates the evaluation member variables.
        tups = []
        for creature in self.creatures:
            fitness = self.get_fitness(creature)
            tups.append((fitness, creature))
        tups.sort(key = lambda tup: tup[0], reverse=True)
        self.ranked_creatures = tups

    def get_percent_done(self):
        return int(self.cur_ticks / self.max_ticks * 100)

    def is_done(self):
        return self.cur_ticks >= self.max_ticks

    def do_timestep(self):
        # Runs the next timestep

        # Update timers
        for creature in self.creatures:
            for node in creature.nodes:
                node.update()
            for muscle in creature.muscles:
                muscle.update()

        # Update physics
        self.space.step(self.TIMESTEMP_DELTA)

        # Goto next tick
        self.cur_ticks += 1

