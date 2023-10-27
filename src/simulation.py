
from abc import ABC, abstractmethod


class Simulation(ABC):
    """
    An instance simulates a set of creatures, specified via a list of genomes,
    for a set amount of time.
    """

    def __init__(self, generation, max_ticks):
        self.generation = generation
        self.max_ticks = max_ticks
        self.cur_ticks = 0  # number of timesteps simulated so far

    @abstractmethod
    def get_fitness(self, creature):
        # Get the fitness of the specified creature
        pass

    @abstractmethod
    def evaluate(self):
        # Updates the evaluation member variables.
        pass

    @abstractmethod
    def _do_timestep_impl(self):
        pass

    def get_percent_done(self):
        return int(self.cur_ticks / self.max_ticks * 100)

    def is_done(self):
        return self.cur_ticks >= self.max_ticks

    def do_timestep(self):
        # Runs the next timestep
        self.cur_ticks += 1
        self._do_timestep_impl()

