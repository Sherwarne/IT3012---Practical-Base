# agent.py
import random


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


class GreedyGridAgent:
    """A simple agent that tries to move around systematically to clear the grid."""

    def __init__(self):
        self.actions_pool = ['Up', 'Down', 'Left', 'Right']

    def sense_and_act(self, percept: dict) -> str:
        # If standing directly on food, or just wander / move towards coordinates
        pos = percept['agent_pos']
        # Simple heuristic or fallback random sweep
        return random.choice(self.actions_pool)
