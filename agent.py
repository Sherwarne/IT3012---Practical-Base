# agent.py
import random


class GreedyGridAgent:
    """A simple agent that tries to move around systematically to clear the grid."""

    def __init__(self):
        self.actions_pool = ['Up', 'Down', 'Left', 'Right']

    def sense_and_act(self, percept: dict) -> str:
        if percept['food_here']:
            return 'Stay'
        return random.choice(self.actions_pool)



class SimpleReflexAgent:
    """A stateless agent that selects actions using condition-action rules."""

    # Weaknesses
    #
    # It is NOT able to move downwards (gets stuck in any upside-down U-shaped walls)
    # It also gets stuck in loops and corners

    def sense_and_act(self, percept: dict) -> str:
        if percept['food_here']:
            return 'Stay'
        if percept['toxic_trap_ahead']:
            return random.choice(['Left', 'Right'])
        if percept['wall_ahead']:
            return random.choice(['Left', 'Right'])
        return 'Up'


class ModelBasedAgent:
    """Explore unvisited relative cells and backtrack at dead ends."""

    # How it operates
    #
    # The agent maintains a relative map of the environment, keeping track of visited cells,
    # bad cells (walls or traps), and blocked paths. It uses this information to explore
    # unvisited cells and backtrack when it reaches dead ends.
    #
    # The core of the agent's decision-making is based on the following rules:
    # 
    # 1. If there is food in the current cell, stay and consume it.
    # 2. If there are unvisited neighboring cells, randomly choose one to move to.
    # 3. If all neighboring cells have been visited or are blocked, backtrack to the previous cell.
    # 4. If there are no unvisited cells and no previous cell to backtrack to, stay in place.
    #
    # Weaknesses
    #
    # It may get stuck in loops if it cannot find a path to unvisited cells.

    DIRECTION_OFFSETS = {
        'Up': (0, 1),
        'Down': (0, -1),
        'Left': (-1, 0),
        'Right': (1, 0)
    }
    def __init__(self):
        self.relative_position = (0, 0)
        if random.random() < 0.25:
            self.facing_direction = 'Up'
        elif random.random() < 0.5:
            self.facing_direction = 'Down'
        elif random.random() < 0.75:
            self.facing_direction = 'Left'
        else:
            self.facing_direction = 'Right'
        self.visited_cells = {self.relative_position}
        self.bad_cells = set()
        self.blocked_paths = {}
        self.path_stack = [self.relative_position]
        self.last_action = None
        self.last_percept = None
        self.backtracking = False
        self.relative_boundaries = {
            'min_x': None,
            'max_x': None,
            'min_y': None,
            'max_y': None
        }

    def _update_state(self, percept: dict):
        """Update the relative map using the result of the previous action."""
        if self.last_action in self.DIRECTION_OFFSETS:
            self.facing_direction = self.last_action
            if percept.get('last_move_succeeded', True):
                dx, dy = self.DIRECTION_OFFSETS[self.last_action]
                new_position = (
                    self.relative_position[0] + dx,
                    self.relative_position[1] + dy
                )
                self.relative_position = new_position

                if self.backtracking:
                    if len(self.path_stack) > 1:
                        self.path_stack.pop()
                elif new_position not in self.visited_cells:
                    self.path_stack.append(new_position)

                self.visited_cells.add(new_position)
            else:
                blocked_position = self._relative_neighbor(self.last_action)
                if percept.get('last_move_result') == 'edge':
                    self._record_boundary(self.last_action, blocked_position)
                else:
                    self.bad_cells.add(blocked_position)
                self.blocked_paths.setdefault(self.relative_position, set()).add(self.last_action)

        self.last_percept = dict(percept)
        self.backtracking = False

        obstacle_ahead = percept['wall_ahead'] or percept.get('toxic_trap_ahead', False)
        if percept.get('edge_ahead', False):
            self._record_boundary(
                self.facing_direction,
                self._relative_neighbor(self.facing_direction)
            )
            self.blocked_paths.setdefault(self.relative_position, set()).add(self.facing_direction)
        elif obstacle_ahead:
            self.bad_cells.add(self._relative_neighbor(self.facing_direction))
            self.blocked_paths.setdefault(self.relative_position, set()).add(self.facing_direction)

    def _relative_neighbor(self, direction: str):
        dx, dy = self.DIRECTION_OFFSETS[direction]
        return self.relative_position[0] + dx, self.relative_position[1] + dy

    def _record_boundary(self, direction: str, boundary_position):
        """Record the first unreachable coordinate beyond a relative map edge."""
        x, y = boundary_position
        if direction == 'Left':
            current = self.relative_boundaries['min_x']
            self.relative_boundaries['min_x'] = x if current is None else max(current, x)
        elif direction == 'Right':
            current = self.relative_boundaries['max_x']
            self.relative_boundaries['max_x'] = x if current is None else min(current, x)
        elif direction == 'Down':
            current = self.relative_boundaries['min_y']
            self.relative_boundaries['min_y'] = y if current is None else max(current, y)
        elif direction == 'Up':
            current = self.relative_boundaries['max_y']
            self.relative_boundaries['max_y'] = y if current is None else min(current, y)

    def _within_relative_boundaries(self, position):
        x, y = position
        bounds = self.relative_boundaries
        return (
            (bounds['min_x'] is None or x > bounds['min_x'])
            and (bounds['max_x'] is None or x < bounds['max_x'])
            and (bounds['min_y'] is None or y > bounds['min_y'])
            and (bounds['max_y'] is None or y < bounds['max_y'])
        )

    def _direction_to(self, destination):
        dx = destination[0] - self.relative_position[0]
        dy = destination[1] - self.relative_position[1]
        for direction, offset in self.DIRECTION_OFFSETS.items():
            if offset == (dx, dy):
                return direction
        return None

    def sense_and_act(self, percept: dict) -> str:
        self._update_state(percept)

        if percept['food_here']:
            action = 'Stay'
        else:
            blocked = self.blocked_paths.get(self.relative_position, set())
            new_paths = [
                direction for direction in self.DIRECTION_OFFSETS
                if direction not in blocked
                and self._relative_neighbor(direction) not in self.visited_cells
                and self._relative_neighbor(direction) not in self.bad_cells
                and self._within_relative_boundaries(self._relative_neighbor(direction))
            ]

            if new_paths:
                action = random.choice(new_paths)
            elif len(self.path_stack) > 1:
                action = self._direction_to(self.path_stack[-2]) or 'Stay'
                self.backtracking = action != 'Stay'
            else:
                action = 'Stay'

        self.last_action = action
        return action

