
import random

from genotype import *


class Generation:

    def __init__(self, idx, genomes):
        self.idx = idx
        self.genomes = genomes

    def add_genome(self, genome):
        self.genomes.append(genome)

    def add_random_genomes(self, count):
        # Adds the specified number of random genomes to this generation.
        for i in range(count):
            self.genomes.append(Genome.generate_random(50, 80))

    def add_children(self, parent_genome, count):
        # Adds the specified number of children of the specfied parent genome,
        # i.e., mutations of that genome, to this generation.

        for i in range(count):
            new_genome = copy.deepcopy(parent_genome)
            new_genome.mutate()
            self.genomes.append(new_genome)

    def split(self, nb_parts):
        split_genomes = [[] for i in range(nb_parts)]
        # Distribute randomly round-robin
        distribution_order = list(range(len(self.genomes)))
        random.shuffle(distribution_order)
        for i in range(len(self.genomes)):
            split_genomes[i%nb_parts].append(self.genomes[distribution_order[i]])
        return [Generation(self.idx, split_genomes[i]) for i in range(nb_parts)]


class FinishedGeneration(Generation):

    def __init__(self, sims):

        # Each element is a tuple (fitness, genome).
        # Sorted descendingly, best to worst fitness.
        self.ranked_genomes = []

        # Merge genomes and self.ranked_genomes
        genomes = []
        for sim in sims:
            genomes.extend(sim.generation.genomes)
            ranked_genomes = [(fitness, creature.genome) for fitness, creature in sim.ranked_creatures]
            self.ranked_genomes.extend(ranked_genomes)
            self.ranked_genomes.sort(key=lambda rg: rg[0], reverse=True)

        # Construct superclass
        generation_idx = sims[0].generation.idx
        super().__init__(generation_idx, genomes)

    def get_stats(self):
        ranked_fitnesses = [rc[0] for rc in self.ranked_genomes]
        if len(ranked_fitnesses) == 0:
            return 0, 0, 0
        fitness_min = int(min(ranked_fitnesses))
        fitness_avg = int(sum(ranked_fitnesses) / len(ranked_fitnesses))
        fitness_max = int(max(ranked_fitnesses))
        return fitness_min, fitness_avg, fitness_max
