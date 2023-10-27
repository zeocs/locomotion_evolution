import random

import math

from genotype import *
from phenotype import *
from utils import stay_in_bounds


# The classes in this file extend the genotype/phenotype base classes with code
# that triggers node stickyness changes and muscle contraction/expansion, based
# on timers, so this is a very simple way of controlling that.


# Timers have an internal value that repeatedly goes from 0 to 1, increasing by
# a certain value each timestep. When it reaches or surpasses 1, it is set to
# modulo 1, making the timer restart.
# The interval between 0 and 1 is divided into two zones, a zone where the timer's
# output value is True, and a zone where the timer's output value is False.
# Each time one of the zones is entered and the other one is left, a callback
# is triggered.


class TimerType:

    MIN_STEP = math.pi / 200
    MAX_STEP = math.pi / 20

    # When mutating, the value can be incremented/decremented by at most
    # that percentage of the size of the value range
    MUTATE_RANGE_PERCENT = 20

    def __init__(self, start, step, true_from, false_from):
        # start (float): Initial internal value
        # step (float): How much the internal value is incremented each update
        self.start = start
        self.step = step
        self.true_from = true_from
        self.false_from = false_from

    @staticmethod
    def generate_random():
        start = random.uniform(0, 2*math.pi)
        step = random.uniform(0, TimerType.MAX_STEP)
        true_from = random.uniform(0, 2*math.pi)
        false_from = random.uniform(0, 2*math.pi)
        return TimerType(start, step, true_from, false_from)

    def scale_step(self, factor):
        # A special form of mutation
        self.step *= factor
        self.step %= self.MAX_STEP

    def mutate(self):
        delta = 2*math.pi * (self.MUTATE_RANGE_PERCENT/100)
        if random.randint(1, 10) <= 4:
            self.start += random.uniform(-delta, delta)
            self.start = stay_in_bounds(self.start, 0, 2*math.pi)
        if random.randint(1, 10) <= 4:
            self.true_from += random.uniform(-delta, delta)
            self.true_from = stay_in_bounds(self.true_from, 0, 2*math.pi)
        if random.randint(1, 10) <= 4:
            self.false_from += random.uniform(-delta, delta)
            self.false_from = stay_in_bounds(self.false_from, 0, 2*math.pi)
        if random.randint(1, 10) <= 4:
            delta = (self.MAX_STEP - self.MIN_STEP) * (self.MUTATE_RANGE_PERCENT/100) # overwrite
            self.step += random.uniform(-delta, delta)
            self.step = stay_in_bounds(self.step, self.MIN_STEP, self.MAX_STEP)


class Timer:

    def __init__(self, timer_type, callback):
        # timer_type (TimerType): Specifies how the timer behaves.
        # callback (function): Invoked when a different zone was entered.
        #   Gets passed a bool that indicates which zone was entered.
        self.timer_type = timer_type
        self.value = timer_type.start
        self.callback = callback

    def update(self):
        # Invoke this once per timestep
        next_value = (self.value + self.timer_type.step) % (2 * math.pi)
        if self.value < self.timer_type.true_from \
            and next_value >= self.timer_type.true_from:
            self.callback(True)
        if self.value < self.timer_type.false_from \
            and next_value >= self.timer_type.false_from:
            self.callback(False)
        self.value = next_value


class TimerNodeType(NodeType):

    def __init__(self, idx, bb_pos, mass, tt):
        super().__init__(idx, bb_pos, mass)
        self.tt = tt

    @classmethod
    def generate_random(cls, idx):
        node_type = NodeType.generate_random(idx)
        if node_type is None: return None
        node_type.__class__ = TimerNodeType     # cast
        node_type.tt = TimerType.generate_random()
        return node_type

    def mutate(self):
        super().mutate()
        self.tt.mutate()


class TimerMuscleType(MuscleType):

    def __init__(self, node_type_1, node_type_2, max_force, damping, stiffness, contract_factor, tt):
        super().__init__(node_type_1, node_type_2, max_force, damping, stiffness, contract_factor)
        self.tt = tt

    @classmethod
    def generate_random(cls, node_type_1, node_type_2):
        muscle_type = MuscleType.generate_random(node_type_1, node_type_2)
        if muscle_type is None: return None
        muscle_type.__class__ = TimerMuscleType     # cast
        muscle_type.tt = TimerType.generate_random()
        return muscle_type

    def scale_timer_step(self, factor):
        # A special form of mutation
        self.tt.scale_step(factor)

    def mutate(self, all_muscle_types):
        super().mutate(all_muscle_types)
        self.tt.mutate()


class TimerNode(Node):

    def __init__(self, creature, timer_node_type, initial_position):
        super().__init__(creature, timer_node_type, initial_position)
        self.timer = Timer(timer_node_type.tt, self._timer_callback)

    def update(self):
        self.timer.update()

    def _timer_callback(self, is_sticky):
        self.set_sticky(is_sticky)


class TimerMuscle(Muscle):

    def __init__(self, creature, timer_muscle_type, node_1, node_2):
        super().__init__(creature, timer_muscle_type, node_1, node_2)
        self.timer = Timer(timer_muscle_type.tt, self._timer_callback)

    def update(self):
        self.timer.update()

    def _timer_callback(self, is_contracted):
        if is_contracted:
            self.contract()
        else:
            self.expand()
