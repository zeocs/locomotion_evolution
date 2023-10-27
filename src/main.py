#!/usr/bin/env python3

# Idee: Mutations-Parameter und/oder Limits von Genom-Parametern und/oder Länge der Simulation, ... auch mutieren!
# -> Selbstoptimierende Simulation
# Richtung bestimmen, in welche diese sich verändern sollten
# Zwei Ansätze:
# - Jede Creature hat die Mutations-Parameter und Genom-Parameter im Genom
# - Eine Population von N Konfigurationen haben (die Mutations-Parameter und Genom-Parameter enthalten),
# Population von Creatres in N Gruppen teilen (z.B. N=3), für die jeweils eine Konfiguration gilt, mit dieser
# Aufteilung die dann für M Generationen simulieren (z.B. M=10), dann drei Mutationen der besten Konfiguration
# als neue Generation von Konfigurationen

import sys, random, copy, os
import pygame
import pymunk
import pymunk.pygame_util
import pickle
import datetime
import pathos

from abc import ABC, abstractmethod

from simulation import *
from genotype import *
from timer import *
from generation import *
from drawing import *
from lineChart import *


# make the simulation the same each time, easier to debug
#random.seed(1)


MAX_WORKERS = 6
SIMULATION_TICKS = 9000
GENERATION_SIZE = 200
SURVIVORS_PER_GENERATION = 20
RANDOMS_PER_GENERATION = 5
GUARANTEE_CHAMPION_SURVIVAL_CHANCE = 0.95

# Overwrites:
# GUARANTEE_CHAMPION_SURVIVAL_CHANCE
# RANDOMS_PER_GENERATION
# GENERATION_SIZE
# SIMULATION_TICKS
# To visualize the mutation factors with super-quick one-creature generations
MUTATION_FACTORS_VISUALIZATION_MODE = False


# ---------------------------------------------------------------------------

if MUTATION_FACTORS_VISUALIZATION_MODE:
    GENERATION_SIZE = 1
    SIMULATION_TICKS = 50
    RANDOMS_PER_GENERATION = 0

SAVE_DIRECTORY = "./saved_generations/"


# ---------------------------------------------------------------------------

def save(genomes, fitness_avg, fitness_max):
    filename = "{}_avg_{}_best_{}.pickle".format( \
        datetime.now().strftime("%Y-%m-%d_%H_%M_%S"), \
        fitness_avg, fitness_max)
    location = SAVE_DIRECTORY + filename
    f = open(location, 'wb')
    p = pickle.Pickler(f)
    p.dump(len(genomes))
    for genome in genomes:
        p.dump(genome)
    f.close()
    print("Generation saved as {}".format(location))

def load(location):
    # Note: Loaded generation may be larger or smaller than GENERATION_SIZE.
    # Returns a generation of the loaded genomes.
    global genomes
    f = open(location, 'rb')
    up = pickle.Unpickler(f)
    nb_genomes = up.load()
    gen = Generation(1, [])
    for i in range(nb_genomes):
        genome = up.load()
        gen.add_genome(genome)
    print("Loaded {} genomes".format(nb_genomes))
    return gen


# ---------------------------------------------------------------------------

class UI(ABC):

    def __init__(self, game):
        self.game = game

    def update(self):
        # General UI update method, shall be invoked each frame, regardless of current mode.
        # Handles mode switching, flips buffers and clears screen, so you're ready to render.

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game.exit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._on_escape()
            self._process_event(event)

        # General subclass updating
        self._update()

        # Rendering
        if self._needs_redraw():
            self._render()

    def _screen_flip_fill(self):
        pygame.display.flip()
        self.game.screen.fill((0,0,0))

    def _draw_text(self, text, pos, center=True):
        # text (str): What to say
        # pos (int, int): Position of the text
        # center (bool): Treat pos as desired center rather than top left
        surface, rect = self.game.font.render(text, (255,255,255))
        if center:
            pos = (pos[0] - rect.w/2, pos[1] - rect.h/2)
        self.game.screen.blit(surface, pos, None)

    @abstractmethod
    def _on_escape(self):
        # Is invoked when the escape key was pressed.
        pass

    @abstractmethod
    def _needs_redraw(self):
        # Returns a bool indicating whether or not rendering is neccessary.
        # Only if True is returned, _render() is invoked.
        pass

    @abstractmethod
    def _process_event(self, event):
        pass

    @abstractmethod
    def _update(self):
        pass

    @abstractmethod
    def _render(self):
        pass


class UIMenu(UI):
    # MENU mode

    CHART_WIDTH=1000
    CHART_HEIGHT=250
    FORCE_REDRAW_FRAMES=60

    def __init__(self, game):
        super().__init__(game)
        self._cur_percent_done = None
        self._last_percent_done = None
        self.linechart = LineChart(self.game.screen, self.game.font,
            (self.game.SCREEN_WIDTH/2-self.CHART_WIDTH/2-LineChart.YAXIS_WIDTH, self.game.SCREEN_HEIGHT/2-self.CHART_HEIGHT/2),
            (self.CHART_WIDTH + LineChart.YAXIS_WIDTH, self.CHART_HEIGHT))
        self.countdown_to_forced_redraw = 0

    def _on_escape(self):
        sys.exit(0)

    def _needs_redraw(self):
        # Only redraw when percentage has changed. Skipping useless
        # redraws significantly speeds up the simulation.
        if self.countdown_to_forced_redraw == 0:
            self.countdown_to_forced_redraw = self.FORCE_REDRAW_FRAMES
            return True
        else:
            self.countdown_to_forced_redraw -= 1
        if self.game.is_simulation_running == False:
            return True
        return self._cur_percent_done != self._last_percent_done

    def _process_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.game.is_simulation_running = not self.game.is_simulation_running
            if event.key == pygame.K_s:
                self.game.save_pending = True
            if event.key == pygame.K_w:
                # We can only display sequential generations. So remember to make the
                # next one sequential, to display it.
                self.game.next_generation_sequential = True
            if event.key == pygame.K_e:
                self.game.set_mode(Game.MODE_EDIT)

    def _update(self):
        self._last_percent_done = self._cur_percent_done
        if self.game.sequential_sim is None:
            self._cur_percent_done = 0 if self.game.jobs is None else \
                int(self.game.count_jobs_done() / len(self.game.jobs) * 100)
        else:
            self._cur_percent_done = self.game.sequential_sim.get_percent_done()

        # The sequential generation requested earlier is there, switch to watch mode now.
        if self.game.next_generation_sequential and self.game.sequential_sim is not None \
            and self.game.mode != Game.MODE_WATCH:
            self.game.set_mode(Game.MODE_WATCH)

    def _render(self):
        self._screen_flip_fill()

        # Render navigation
        if self.game.is_simulation_running:
            text = "[p] Pause simulation"
        else:
            text = "[p] Continue simulation"
        self._draw_text(text, (self.game.SCREEN_WIDTH/2, self.game.SCREEN_HEIGHT/4-40), True)
        pending_text = " (Pending...)" if self.game.next_generation_sequential else ""
        self._draw_text("[w] Watch generation{}".format(pending_text),
            (self.game.SCREEN_WIDTH/2, self.game.SCREEN_HEIGHT/4-0), True)
        pending_text = " (Pending...)" if self.game.save_pending else ""
        self._draw_text("[s] Save genomes{}".format(pending_text),
            (self.game.SCREEN_WIDTH/2, self.game.SCREEN_HEIGHT/4+40), True)
        self._draw_text("[e] Edit genome", (self.game.SCREEN_WIDTH/2, self.game.SCREEN_HEIGHT/4+80), True)

        # Prepare datasets
        datasets = [
            (pygame.Color(255,0,0), []),
            (pygame.Color(255,255,0), []),
            (pygame.Color(0,255,0), [])
        ]
        for gen in self.game.old_generations:
            stats = gen.get_stats()
            for dataset_idx, dataset in enumerate(datasets):
                dataset[1].append(stats[dataset_idx])

        # Render simulation info
        self.linechart.set_datasets(datasets)
        self.linechart.render()
        generation_number = self.game.cur_generation.idx \
            if self.game.cur_generation is not None \
            else 0 if len(self.game.old_generations) == 0 \
                else self.game.old_generations[-1].idx
        text = "Generation #{}".format(generation_number)
        text += " ({}% done)".format(self._cur_percent_done)
        self._draw_text(text, (self.game.SCREEN_WIDTH/2, 3*self.game.SCREEN_HEIGHT/4), True)


class UIGame(UI):
    # UI for any mode that involves displaying game elements

    TRANSLATE_SPEED = 10
    ZOOM_SPEED = 0.01

    def __init__(self, game):
        super().__init__(game)

        # Pymunk graphics members
        self.draw_options = pymunk.pygame_util.DrawOptions(self.game.screen)
        self.translation = pymunk.Transform.translation(600, 0)
        self.scaling = 0.5
        self._refresh_drawing_transform()
        self.drawing = Drawing(self)

    def _move_camera_to_start():
        # Moves the camera back to starting point
        self.translation = self.translation.translated(-self.translation.tx, -self.translation.ty)
        self._refresh_drawing_transform()

    def _update_camera(self):
        # Examine camera movement keys
        keys = pygame.key.get_pressed()
        left = int(keys[pygame.K_LEFT])
        up = int(keys[pygame.K_UP])
        down = int(keys[pygame.K_DOWN])
        right = int(keys[pygame.K_RIGHT])
        zoom_in = int(keys[pygame.K_PAGEUP])
        zoom_out = int(keys[pygame.K_PAGEDOWN])

        # Update camera movement
        # Note: To zoom with center of screen as origin we need to offset
        # with center of screen, scale, and then offset back
        if up or down or right or left or zoom_in or zoom_out:
            self.translation = self.translation.translated(
                self.TRANSLATE_SPEED / self.scaling * left - self.TRANSLATE_SPEED / self.scaling * right,
                self.TRANSLATE_SPEED / self.scaling * up - self.TRANSLATE_SPEED / self.scaling * down,
            )
            self.scaling *= 1 + (self.ZOOM_SPEED * zoom_in - self.ZOOM_SPEED * zoom_out)
            self._refresh_drawing_transform()

    def _refresh_drawing_transform(self):
        self.draw_options.transform = (
            pymunk.Transform.translation(self.game.SCREEN_WIDTH/2, self.game.SCREEN_HEIGHT/2)
            @ pymunk.Transform.scaling(self.scaling)
            @ self.translation
            @ pymunk.Transform.translation(-self.game.SCREEN_WIDTH/2, -self.game.SCREEN_HEIGHT/2)
        )


class UIWatch(UIGame):

    def __init__(self, game):
        super().__init__(game)
        self._show_only_best = False
        self._show_specs = False
        self._is_paused = False

    def _on_escape(self):
        if not MUTATION_FACTORS_VISUALIZATION_MODE:
            self.game.next_generation_sequential = False
        self.game.set_mode(Game.MODE_MENU)

    def _needs_redraw(self):
        return True

    def _process_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                self._show_only_best = not self._show_only_best
            if event.key == pygame.K_i:
                self._show_specs = not self._show_specs
            if event.key == pygame.K_p:
                self._is_paused = not self._is_paused
            if event.key == pygame.K_s:
                self.game.save_pending = True

    def _update(self):
        pass

    def _render(self):
        self._screen_flip_fill()
        self._update_camera()

        if self.game.sequential_sim is None:
            return

        # Determine best creature, if needed
        if self._show_only_best:
            self.game.sequential_sim.evaluate()
            best_creature = self.game.sequential_sim.ranked_creatures[0][1]
        else:
            best_creature = None

        # Render pymunk objects
        self.drawing.draw_ground(self.game.sequential_sim.segments)
        if self._show_only_best and best_creature is not None:
            self.drawing.draw_creature(best_creature, self._show_specs)
        else:
            for creature in self.game.sequential_sim.creatures:
                self.drawing.draw_creature(creature, self._show_specs)

        # Render info text
        percent_done = self.game.sequential_sim.get_percent_done()
        info_text_str = "{:>3}% done".format(percent_done)
        info_text, _ = self.game.font.render(info_text_str, (255,255,255))
        self.game.screen.blit(info_text, (5,5), None)

        # Draw current centers
        for idx, creature in enumerate(self.game.sequential_sim.creatures):
            if not self._show_only_best or creature == best_creature:
                center = creature.get_average_node_position()
                pygame.draw.circle(self.game.screen, (0,128,0), self.draw_options.transform @ center, 5)


class UIEditor(UIGame):
    # Unfinished

    def _on_escape(self):
        self.game.set_mode(Game.MODE_MENU)

    def _needs_redraw(self):
        return True

    def _render(self):
        self._screen_flip_fill()

        # Draw text
        self._draw_text("Click to place node", (10, 10), False)

        # Update camera
        self._update_camera()

        # Render pymunk objects
        self.drawing.draw_genome(genome, (0, 0))


# ---------------------------------------------------------------------------

class Game:
    """
    Simulating of generations can run independently of the current UI mode.
    """

    SCREEN_WIDTH = 1600
    SCREEN_HEIGHT = 1200

    MODE_MENU = 0
    MODE_WATCH = 1
    MODE_EDIT = 2

    def __init__(self):

        # Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.SCREEN_WIDTH, self.SCREEN_HEIGHT))
        self.font = pygame.freetype.SysFont("Calibri", 20)
        pygame.display.set_caption("Locomotion Evolution Simulator 1.1")

        # User interface
        self.mode = None
        self.ui = None
        self.save_pending = False
        self.set_mode(self.MODE_MENU)

        # Worker pool
        # https://stackoverflow.com/questions/48990688/pathos-parallel-processing-options-could-someone-explain-the-differences
        #self.pool = pathos.pools.ParallelPool(inodes=MAX_WORKERS)
        self.pool = pathos.pools.ProcessPool(ncpus=MAX_WORKERS)
        self.jobs = None            # None while not processing
        self.done_sims = None       #  " "

        # Simulation members
        self.old_generations = []       # List of FinishedGeneration instances
        self.cur_generation = None      # None while not processing
        self.next_generation = None     # Only set between finishing one generation and starting the next
        self.next_generation_sequential = False     # If True, the next generation will be started as sequential
        self.sequential_sim = None      # Only set while processing a sequential generation
        self.is_simulation_running = True
        if MUTATION_FACTORS_VISUALIZATION_MODE:
            self.next_generation_sequential = True

        # Make an initial generation and set it to be the next one
        initial_generation = Generation(1, [])
        initial_generation.add_random_genomes(GENERATION_SIZE)
        self.next_generation = initial_generation

    def exit(self):
        self.pool.close()
        self.pool.join()

    def set_mode(self, mode):
        self.mode = mode
        if mode == self.MODE_MENU:
            self.ui = UIMenu(self)
        elif mode == self.MODE_WATCH:
            self.ui = UIWatch(self)
        elif mode == self.MODE_EDIT:
            self.ui = UIEditor(self)

    def update(self):
        if self.cur_generation is not None:
            if self.sequential_sim is not None:
                # This is a sequential generation
                if self.sequential_sim.is_done():
                    self.sequential_sim.evaluate()
                    self._finish_generation([self.sequential_sim])
                    self.next_generation = self._make_next_generation()
                else:
                    # TODO Not nice to access mode-specific stuff here
                    if not (self.mode == self.MODE_WATCH and self.ui._is_paused):
                        self.sequential_sim.do_timestep()

            else:
                # This is a parallel generation

                # Collect finished jobs (non-blocking)
                for job_idx, job in enumerate(self.jobs):
                    if self.done_sims[job_idx] is None and job.ready():
                        self.done_sims[job_idx] = job.get()

                # All jobs finished?
                if self.count_jobs_done() == len(self.jobs):
                    self._finish_generation(self.done_sims)
                    self.next_generation = self._make_next_generation()

        else:
            if self.is_simulation_running \
                and self.cur_generation is None \
                and self.next_generation is not None:

                # Start the next generation
                self._start_generation(self.next_generation)
                self.next_generation = None

                # Save, if pending
                if self.save_pending:
                    gen = self.old_generations[-1]
                    fitness_min, fitness_avg, fitness_max = gen.get_stats()
                    save(gen.genomes, fitness_avg, fitness_max)
                    self.save_pending = False

        # Update UI
        self.ui.update()

    def count_jobs_done(self):
        return 0 if self.done_sims is None else \
            sum([1 for s in self.done_sims if s is not None])

    def _make_next_generation(self):
        # Generate the next generation from the last and return it.
        parent_gen = self.old_generations[-1]
        reproducing_genomes = [rg[1] for rg in parent_gen.ranked_genomes[0:SURVIVORS_PER_GENERATION]]
        next_generation = Generation(parent_gen.idx+1, [])
        guarantee_champion_survival = False if MUTATION_FACTORS_VISUALIZATION_MODE else \
            random.uniform(0, 1) <= GUARANTEE_CHAMPION_SURVIVAL_CHANCE
        while len(next_generation.genomes) < GENERATION_SIZE - RANDOMS_PER_GENERATION:
            if guarantee_champion_survival and len(next_generation.genomes) == 0:
                next_generation.add_genome(parent_gen.ranked_genomes[0][1])
            else:
                parent_genome = random.choice(reproducing_genomes)
                next_generation.add_children(parent_genome, 1)
        next_generation.add_random_genomes(RANDOMS_PER_GENERATION)
        return next_generation

    def sim_func(generation):
        #print("Simulation started")
        sim = Simulation(generation, SIMULATION_TICKS)
        while not sim.is_done():
            sim.do_timestep()
        sim.evaluate()
        #print("Simulation done")
        return sim

    def _start_generation(self, new_generation):
        if self.next_generation_sequential:
            self.sequential_sim = Simulation(new_generation, SIMULATION_TICKS)
        else:
            split_generations = new_generation.split(MAX_WORKERS)
            self.jobs, self.done_sims = [], []
            for split_generation in split_generations:
                pathos_job = self.pool.apipe(Game.sim_func, split_generation)
                self.jobs.append(pathos_job)
                self.done_sims.append(None)
        self.cur_generation = new_generation

    def _finish_generation(self, sims):
        fg = FinishedGeneration(sims)
        self.old_generations.append(fg)
        self.jobs, self.done_sims = None, None
        self.cur_generation = None
        self.sequential_sim = None

        # Show statistics
        fitness_min, fitness_avg, fitness_max = fg.get_stats()
        if len(self.old_generations) % 10 == 0:
            print("{:<5} {:<8} {:<8} {:<8}".format("#Gen", "Fit min", "Fit avg", "Fit max"))
        print("{:<5} {:<8} {:<8} {:<8}".format(self.old_generations[-1].idx, fitness_min, fitness_avg, fitness_max))


# ---------------------------------------------------------------------------

Genome.NODE_TYPE_CLASS = TimerNodeType
Genome.MUSCLE_TYPE_CLASS = TimerMuscleType

game = Game()

# ---------------------------------------------------------------------------

# TODO Use the argparse module

HELP = False

for arg in sys.argv[1:]:
    if arg == "-help":
        HELP=True
    elif arg.startswith("-load="):
        game.next_generation = load(arg.split("=")[1])
    else:
        print("Invalid arguments given")
        HELP=True
        break

if HELP:
    print("Usage:")
    print("{} [-load=<location>]")
    sys.exit(0)

# ---------------------------------------------------------------------------

# The main loop
try:
    while True:
        game.update()
except KeyboardInterrupt:
    game.exit()
    sys.exit(0)

