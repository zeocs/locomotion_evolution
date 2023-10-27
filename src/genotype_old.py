import random
import math
import copy

import pymunk
from pymunk.vec2d import Vec2d


# Note: Contraction groups and sticky groups are currently unused, they serve no
# effective purpose.
# They would be useful if muscle contraction/expansion was "centrally-controlled",
# like if a neural network was used for that (maybe later).
# Locomotion control may later be done by a neural network (like NEAT-python).
# TODO: Move them to neuronal-network-specific subclasses



class NodeChildPlan:
    # Describes how one of the child nodes of some node type shall be placed.
    # TODO use dataclass(?)

    def __init__(self, node_type, dist, symmetric_twin, \
            angle_parent, angle_prev_child, \
            link_parent, link_prev_child, link_symmetric_twin):
        # Specifies how one of the children (possible along with a twin) of a node
        # shall be placed.
        #
        # node_type (NodeType): What kind of node to place as child node
        # dist (int): distance from the parent node
        # symmetric_twin (bool): Whether to also place a second similar node at
        #   negated angle, useful for creating symmetry
        #
        # > Note that you must specify either angle_parent or angle_prev_child.
        # angle_parent (float|None): angle in radiants from the parent node's angle
        # angle_prev_child (float|None): angle in radiants from the previous child,
        #   is treated like angle_parent if specified for the first child
        #
        # > For the following, pass None to not create a muscle. To create a muscle,
        # > pass an int, which will specify the contraction group for the muscle.
        # link_parent (int|None): Muscle to parent
        # link_prev_child (int|None): Muscle to the previous child. Does not have an
        #   effect if specified for the first child. Symmetric twins are considered
        #   to be a separate "group", i.e., they will be linked with the previous
        #   symmetric twin.
        # link_symmetric_twin (int|None): Muscle to the symmetric twin.
        #   Has no effect if symmetric_twin is False.
        assert((angle_parent is None) != (angle_prev_child is None))
        self.node_type = node_type
        self.dist = dist
        self.symmetric_twin = symmetric_twin
        self.angle_parent = angle_parent
        self.angle_prev_child = angle_prev_child
        self.link_parent = link_parent
        self.link_prev_child = link_prev_child
        self.link_symmetric_twin = link_symmetric_twin

    def mutate(self, parent_node_type, all_node_types, all_cgs):
        # all_cgs (int[]): List of all contraction groups occuring in the creature

        # Mutate type of child node
        if random.randint(1, 10) <= 1:
            self.node_type = random.choice(all_node_types)

        # Mutate distance
        if random.randint(1, 10) <= 5:
            factor = -1 if random.randint(0, 1) == 0 else 1
            self.dist *= factor * random.uniform(0.8, 1.2)

        # Mutate whether there's a symmetric twin
        if random.randint(1, 10) <= 1:
            self.symmetric_twin = not self.symmetric_twin

        # Mutate whether node is placed relative to parent or to previous child
        # and at what angle
        use_angle_parent = self.angle_parent is not None
        angle = self.angle_parent if use_angle_parent else self.angle_prev_child
        if random.randint(1, 10) <= 5:
            angle = self._mutate_angle(angle)
        if random.randint(1, 10) <= 1:
            use_angle_parent = not use_angle_parent
        self.angle_parent = angle if use_angle_parent else None
        self.angle_prev_child = angle if not use_angle_parent else None

        # Mutate linkings
        if random.randint(1, 10) <= 2:
            self.link_parent = self._mutate_linking(self.link_parent, all_cgs)
        if random.randint(1, 10) <= 2:
            self.link_prev_child = self._mutate_linking(self.link_prev_child, all_cgs)
        if random.randint(1, 10) <= 2:
            self.link_symmetric_twin = self._mutate_linking(self.link_symmetric_twin, all_cgs)

    def _mutate_linking(self, linking, all_cgs):
        if linking is None:
            linking = random.choice(all_cgs)
        else:
            linking = None
        return linking

    def _mutate_angle(self, angle):
        factor = -1 if random.randint(0, 1) == 0 else 1
        angle += factor * random.uniform(0, math.pi)
        angle %= 2 * math.pi
        return angle

    def get_used_cgs(self):
        # Returns a set of used contraction group ints
        cgs = set()
        if self.link_parent is not None:
            cgs.add(self.link_parent)
        if self.link_prev_child is not None:
            cgs.add(self.link_prev_child)
        if self.link_symmetric_twin is not None:
            cgs.add(self.link_symmetric_twin)
        return cgs


class NodeType:

    def __init__(self, plans, sticky_group):
        # List of NodeChildPlan instances, describing how children shall
        # be placed relative to this node.
        # sticky_group (int|None):
        self.plans = plans
        self.sticky_group = sticky_group

    def __repr__(self):
        return str(id(self)%999)

    def mutate(self, all_node_types, all_cgs):
        # Maybe clone a plan and insert it at a random position
        if random.randint(1, 10) <= 2 and len(self.plans) > 0:
            chosen_plan = random.choice(self.plans)
            idx = random.randint(0, len(self.plans))
            self.plans.insert(idx, copy.copy(chosen_plan))

        # Maybe delete a plan
        if random.randint(1, 10) <= 1 and len(self.plans) > 0:
            chosen_plan = random.choice(self.plans)
            self.plans.remove(chosen_plan)

        # Mutate some plans
        for plan in self.plans:
            plan.mutate(self, all_node_types, all_cgs)

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


class Genome:

    def __init__(self, node_types):
        # node_types (NodeType[]): Specifies all occuring types of nodes and what
        #   children they have. The first in the list is considered to be the root
        #   node type: Building the creature will start with a node of that NodeType.
        assert(len(node_types) > 0)
        self.node_types = node_types

    def mutate(self):
        # TODO: Mutate contraction groups

        # Collect contraction groups
        all_cgs = set()
        for node_type in self.node_types:
            all_cgs.update(node_type.get_used_cgs())
        all_cgs = list(all_cgs)
        if len(all_cgs) == 0:
            all_cgs.append(0)   # TODO temporary

        # Maybe clone a node type
        # Note: copy.deepcopy() also recursively copies linked
        # objects like the child plans
        if random.randint(1, 10) <= 1:
            chosen_node_type = random.choice(self.node_types)
            self.node_types.append(copy.deepcopy(chosen_node_type))

        # Mutate some node types
        for node_type in self.node_types:
            if random.randint(1, 10) <= 3:
                node_type.mutate(self.node_types, all_cgs)

        # Delete unused node types
        used_node_types = set()
        for node_type in self.node_types:
            used_node_types.add(node_type)
            used_node_types.update(node_type.get_children_node_types())
        for node_type in set(self.node_types).difference(used_node_types):
            self.node_types.remove(node_type)
