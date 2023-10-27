import random
import math
import copy

import pymunk
from pymunk.vec2d import Vec2d

from utils import stay_in_bounds


class NodeType:
    # There is exactly one NodeType (genotype) for each Node (phenotype).

    # When mutating, the value can be incremented/decremented by at most
    # that percentage of the diameter of the bounding box.
    MUTATE_BB_POSITION_MAX_PERCENTAGE = 20

    MASS_MIN=1
    MASS_MAX=15

    def __init__(self, idx, bb_position, mass):
        # idx (int): Identifies the node in the genome
        # bb_position (Vec2d): Where to place the node, relative to the creature
        #   bounding box top left corner
        # mass (float): Mass of body
        self.idx = idx
        self.bb_position = bb_position
        self.mass = mass

    @staticmethod
    def generate_random(idx):
        bb_pos = Vec2d(random.uniform(0, Genome.BB_WIDTH), random.uniform(0, Genome.BB_HEIGHT))
        mass = random.uniform(NodeType.MASS_MIN, NodeType.MASS_MAX)
        return NodeType(idx, bb_pos, mass)

    def __repr__(self):
        return "idx={}, mass={}, bb_pos={}".format(\
            self.idx, self.mass, self.bb_position)

    def mutate(self):
        # Make position completely random
        if random.randint(1, 100) <= 5:
            self.bb_position = Vec2d(
                random.uniform(0, Genome.BB_WIDTH),
                random.uniform(0, Genome.BB_HEIGHT)
            )

        # Move position a little
        if random.randint(1, 100) <= 50:
            angle = random.uniform(0, 2*math.pi)
            diameter = math.sqrt(Genome.BB_WIDTH**2 + Genome.BB_HEIGHT**2)
            length = random.uniform(0, diameter*(self.MUTATE_BB_POSITION_MAX_PERCENTAGE/100))
            delta = Vec2d(math.cos(angle), math.sin(angle)) * length
            self.bb_position += delta
            self.bb_position = Vec2d( \
                stay_in_bounds(self.bb_position.x, 0, Genome.BB_WIDTH), \
                stay_in_bounds(self.bb_position.y, 0, Genome.BB_HEIGHT))

        # Mutate mass
        if random.randint(1, 100) <= 25:
            delta = (self.MASS_MAX - self.MASS_MIN) * (self.MUTATE_BB_POSITION_MAX_PERCENTAGE/100)
            self.mass += random.uniform(-0.4, 0.4)
            self.mass = stay_in_bounds(self.mass, self.MASS_MIN, self.MASS_MAX)

    def get_children_node_types(self):
        # Returns a set of node types used by children
        node_types = set()
        for plan in self.plans:
            node_types.add(plan.node_type)
        return node_types

    def get_used_cgs(self):
        # Returns a set of used contraction group ints
        cgs = set()
        for plan in self.plans:
            cgs.update(plan.get_used_cgs())
        return cgs


class MuscleType:
    # There is exactly one MuscleType (genotype) for each Muscle (phenotype).
    # TODO Support error_bias (non-instantaneous error correction)

    # When mutating, the value can be incremented/decremented by at most
    # that percentage of the size of the value range.
    MUTATE_RANGE_PERCENT = 15

    MAX_FORCE_MIN = 20
    MAX_FORCE_MAX = 7000

    STIFFNESS_MIN = 1
    STIFFNESS_MAX = 600

    # How much the spring "wiggles" (smaller=more)
    DAMPING_MIN = 1
    DAMPING_MAX = 40

    CONTRACT_FACTOR_MIN = 0.5
    CONTRACT_FACTOR_MAX = 1

    def __init__(self, node_type_1, node_type_2, max_force, damping, stiffness, contract_factor):
        # damping (float): How much the spring "wiggles" (smaller=more)
        self.node_type_1 = node_type_1
        self.node_type_2 = node_type_2
        self.max_force = max_force
        self.damping = damping
        self.stiffness = stiffness
        self.contract_factor = contract_factor

    @staticmethod
    def generate_random(node_type_1, node_type_2):
        muscle_type = MuscleType(node_type_1, node_type_2, None, None, None, None)
        muscle_type.randomize()
        return muscle_type

    def randomize(self):
        self.max_force = random.uniform(MuscleType.MAX_FORCE_MIN, MuscleType.MAX_FORCE_MAX)
        self.damping = random.uniform(MuscleType.DAMPING_MIN, MuscleType.DAMPING_MAX)
        self.stiffness = random.uniform(MuscleType.STIFFNESS_MIN, MuscleType.STIFFNESS_MAX)
        self.contract_factor = random.uniform(MuscleType.CONTRACT_FACTOR_MIN, MuscleType.CONTRACT_FACTOR_MAX)

    def mutate(self, all_muscle_types):
        # Make parameters completely random
        if random.randint(1, 100) <= 5:
            self.randomize()

        # Copy from somewhere
        if random.randint(1, 100) <= 10:
            other_muscle_type = None
            other_muscle = random.choice(all_muscle_types) # may even be self but who cares
            self.max_force = other_muscle.max_force
            self.damping = other_muscle.damping
            self.stiffness = other_muscle.stiffness
            self.contract_factor = other_muscle.contract_factor

        # Change parameters a little
        if random.randint(1, 100) <= 50:
            if random.randint(1, 100) <= 50:
                delta = (self.MAX_FORCE_MAX - self.MAX_FORCE_MIN) * (self.MUTATE_RANGE_PERCENT/100)
                self.max_force += random.uniform(-delta, delta)
                self.max_force = stay_in_bounds(self.max_force, self.MAX_FORCE_MIN, self.MAX_FORCE_MAX)
            if random.randint(1, 100) <= 50:
                delta = (self.DAMPING_MAX - self.DAMPING_MIN) * (self.MUTATE_RANGE_PERCENT/100)
                self.damping += random.uniform(-delta, delta)
                self.damping = stay_in_bounds(self.damping, self.DAMPING_MIN, self.DAMPING_MAX)
            if random.randint(1, 100) <= 50:
                delta = (self.STIFFNESS_MAX - self.STIFFNESS_MIN) * (self.MUTATE_RANGE_PERCENT/100)
                self.stiffness += random.uniform(-delta, delta)
                self.stiffness = stay_in_bounds(self.stiffness, self.STIFFNESS_MIN, self.STIFFNESS_MAX)
            if random.randint(1, 100) <= 50:
                delta = (self.CONTRACT_FACTOR_MAX - self.CONTRACT_FACTOR_MIN) * (self.MUTATE_RANGE_PERCENT/100)
                self.contract_factor += random.uniform(-delta, delta)
                self.contract_factor = stay_in_bounds(self.contract_factor, self.CONTRACT_FACTOR_MIN, self.CONTRACT_FACTOR_MAX)


class MuscleMatrix:
    # This matrix has an internal dict of all muscles that exist between pairs of nodes.
    # The value of the dict are the muscle types, the keys of the dict is a concatenation
    # of the node indices, the smaller one first, separated by an underscore character.

    def __init__(self):
        self._data = {}

    def __repr__(self):
        return ', '.join(self._data.keys())

    def _get_key(self, node_type_1, node_type_2):
        return "{}_{}".format( \
            min(node_type_1.idx, node_type_2.idx), \
            max(node_type_1.idx, node_type_2.idx))

    def get_muscle_type(self, node_type_1, node_type_2):
        # Swapping the given nodes gives the same result.
        # Returns NodeType or None if there's no muscle between the nodes.
        key = self._get_key(node_type_1, node_type_2)
        if key in self._data:
            return self._data[key]
        else:
            return None

    def set_muscle_type(self, node_type_1, node_type_2, muscle_type):
        # Swapping the given nodes gives the same result.
        # muscle_type (MuscleType|None): The new matrix entry
        assert(node_type_1 != node_type_2)
        key = self._get_key(node_type_1, node_type_2)
        if muscle_type == None:
            del self._data[key]
        else:
            self._data[key] = muscle_type

    def iterate_all_muscles(self):
        for muscle_type in self._data.values():
            yield muscle_type

    def get_count(self):
        return len(self._data)

    def get_random_muscle(self):
        # Returns None if no possible pairs are connected by a muscle.
        if self.get_count() == 0:
            return None
        else:
            key = random.choice(list(self._data.keys()))
            return self._data[key]

    def get_random_unconnected_pair(self, node_types):
        # node_types (NodeType[]): All node types in the creature
        # Returns (None, None) if all possible pairs are connected by a muscle.
        # TODO very inefficient, because we're just guessing!
        # 
        nb_nodes = len(node_types)
        nb_possible_muscles = (nb_nodes * (nb_nodes - 1)) / 2
        if self.get_count() == nb_possible_muscles:
            return None, None
        while True:
            node_type_1 = random.choice(node_types)
            node_type_2 = random.choice(node_types)
            if node_type_1 == node_type_2:
                continue
            if self.get_muscle_type(node_type_1, node_type_2) == None:
                return (node_type_1, node_type_2)


class Genome:

    BB_WIDTH = 600
    BB_HEIGHT = 500

    MIN_NODES = 4
    MAX_NODES = 8

    NODE_TYPE_CLASS = NodeType      # will be overwritten
    MUSCLE_TYPE_CLASS = MuscleType  # will be overwritten

    def __init__(self):
        self.node_types = [] # List position and node's idx must match for every node
        self.matrix = MuscleMatrix()

    @staticmethod
    def generate_random(percentage_muscles_min, percentage_muscles_max):
        # Creates a completely random genome.
        genome = Genome()

        # Create nodes
        nb_nodes = random.randint(Genome.MIN_NODES, Genome.MAX_NODES)
        for idx in range(nb_nodes):
            node_type = Genome.NODE_TYPE_CLASS.generate_random(idx)
            genome.node_types.append(node_type)

        # Create muscles
        # TODO inefficient for many muscles because guessing not-yet connected pairs
        nb_possible_muscles = (nb_nodes * (nb_nodes - 1)) / 2
        nb_muscles = int(nb_possible_muscles * random.randint(percentage_muscles_min, percentage_muscles_max) / 100)
        while genome.matrix.get_count() < nb_muscles:
            node_type_1 = random.choice(genome.node_types)
            node_type_2 = random.choice(genome.node_types)
            if node_type_1 == node_type_2:
                continue
            if genome.matrix.get_muscle_type(node_type_1, node_type_2) == None:
                muscle = Genome.MUSCLE_TYPE_CLASS.generate_random(node_type_1, node_type_2)
                genome.matrix.set_muscle_type(node_type_1, node_type_2, muscle)

        return genome

    def mutate(self):
        # TODO: Creating/Cloning and deleting nodes, but that requires keeping their idx
        # in sync with the muscle matrix, maybe make idx management more clean first...

        # Mutate some node types
        for node_type in self.node_types:
            if random.randint(1, 10) <= 4:
                node_type.mutate()

        # Mutate some muscle types
        scale_all_timers = random.randint(1, 10) <= 1
        if scale_all_timers:
            factor = random.uniform(0.5, 1.5)
            for muscle_type in self.matrix.iterate_all_muscles():
                muscle_type.scale_timer_step(factor)
        else:
            all_muscle_types = list(self.matrix.iterate_all_muscles())
            for muscle_type in self.matrix.iterate_all_muscles():
                if random.randint(1, 10) <= 6:
                    muscle_type.mutate(all_muscle_types)

        # Delete some muscle types
        if random.randint(1, 100) <= 5:
            muscle = self.matrix.get_random_muscle()
            if muscle != None:
                self.matrix.set_muscle_type(muscle.node_type_1, muscle.node_type_2, None)

        # Create a muscle type
        if random.randint(1, 100) <= 5:
            node_type_1, node_type_2 = self.matrix.get_random_unconnected_pair(self.node_types)
            if node_type_1 != None:
                muscle = Genome.MUSCLE_TYPE_CLASS.generate_random(node_type_1, node_type_2)
                self.matrix.set_muscle_type(node_type_1, node_type_2, muscle)

        # TODO Delete unconnected node types
        
