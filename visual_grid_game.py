# visual_grid_game.py
import json
import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from agent import GreedyGridAgent, ModelBasedAgent, SearchAgent, SimpleReflexAgent


LEVEL_FILE = Path(__file__).with_name("level_positions.json")
DEFAULT_FOOD_CONCENTRATION = 15
AGENT_TYPES = {
    "Greedy Grid Agent": (GreedyGridAgent, None),
    "Simple Reflex Agent": (SimpleReflexAgent, None),
    "Model-Based Agent": (ModelBasedAgent, None),
    "Search Agent (BFS)": (SearchAgent, 'BFS'),
    "Search Agent (DFS)": (SearchAgent, 'DFS'),
    "Search Agent (UCS)": (SearchAgent, 'UCS'),
    "Search Agent (AStar)": (SearchAgent, 'AStar')
}


def load_level_positions(level_file=LEVEL_FILE):
    """Load wall and toxic-trap coordinates from the level JSON file."""
    try:
        with open(level_file, "r", encoding="utf-8") as file:
            level = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        level = {}

    walls = {tuple(position) for position in level.get("walls", [])}
    toxic_traps = {tuple(position) for position in level.get("toxic_traps", [])}
    return walls, toxic_traps


def load_start_position(level_file=LEVEL_FILE):
    """Load the saved player start position, defaulting to the bottom-left tile."""
    try:
        with open(level_file, "r", encoding="utf-8") as file:
            level = json.load(file)
        position = tuple(level.get("player_start", [0, 0]))
        if len(position) == 2:
            return position
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        pass
    return 0, 0


def load_food_configuration(level_file=LEVEL_FILE):
    """Load preset food coordinates and whether food should be generated randomly."""
    try:
        with open(level_file, "r", encoding="utf-8") as file:
            level = json.load(file)
        food_positions = {tuple(position) for position in level.get("food_positions", [])}
        random_food = 1 if level.get("random_food", 1) else 0
        return food_positions, random_food
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return set(), 1


def save_level_positions(walls, toxic_traps, player_start=None, food_positions=None,
                         random_food=None, level_file=LEVEL_FILE):
    """Persist terrain coordinates in a readable, stable order."""
    if player_start is None:
        player_start = load_start_position(level_file)
    saved_food, saved_random_food = load_food_configuration(level_file)
    if food_positions is None:
        food_positions = saved_food
    if random_food is None:
        random_food = saved_random_food

    def coordinate_list_lines(name, positions, trailing_comma=True):
        sorted_positions = sorted(positions)
        if not sorted_positions:
            return [f'    "{name}": []' + ("," if trailing_comma else "")]
        lines = [f'    "{name}": [']
        for index, position in enumerate(sorted_positions):
            comma = "," if index < len(sorted_positions) - 1 else ""
            lines.append(f"        {json.dumps(list(position))}{comma}")
        lines.append("    ]" + ("," if trailing_comma else ""))
        return lines

    lines = ["{"]
    lines.extend(coordinate_list_lines("walls", walls))
    lines.extend(coordinate_list_lines("toxic_traps", toxic_traps))
    lines.extend(coordinate_list_lines("food_positions", food_positions))
    lines.append(f'    "player_start": {json.dumps(list(player_start))},')
    lines.append(f'    "random_food": {1 if random_food else 0}')
    lines.append("}")

    with open(level_file, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")

# Lab implementations
#
# Added toxic traps with preset locations
# Modified generation to account for toxic traps
# Augmented agent with ability to sense toxic traps
# Intersecting a toxic trap results in a score penalty of -15 points
# Toxic traps are represented as purple triangles on the grid

# Extra implementations
#
# Implemented interruption and restart functionality
# Grid editing system: cycle through empty → wall → toxic trap by clicking on a tile

# NOTE: You can start the game with python visual_grid_game.py

class VisualGridHuntGame:
    """A flexible Pacman-style grid environment with support for configurable opponents and larger scales."""

    def __init__(self, width=15, height=15, num_food=10, num_opponents=2, custom_walls=None,
                 custom_toxic_traps=None, custom_food=None, random_food=1,
                 start_position=(0, 0), max_steps=150):
        self.width = width
        self.height = height
        self.max_steps = max_steps
        self.random_food = 1 if random_food else 0
        self.agent_pos = list(start_position)
        # Randomize initial facing direction
        if random.random() < 0.5:
            self.facing_direction = 'Right'
        else:
            self.facing_direction = 'Up'

        if custom_walls is not None:
            self.walls = set(custom_walls)
        else:
            # Generate some default scattered walls for a larger grid
            self.walls = {(2, 2), (2, 3), (5, 5), (6, 5), (3, 7), (5, 4), (5, 3), (7, 7), (8, 8), (1, 5), (4, 7), (3, 3), (6, 1), (9, 4), (0, 6)}

        if custom_toxic_traps is not None:
            self.toxic_traps = set(custom_toxic_traps)
        else:
            self.toxic_traps = {(1, 1), (4, 4), (7, 2), (10, 3), (5, 8), (8, 6), (3, 9), (9, 1), (2, 8), (6, 2)}

        eligible_food_cells = [
            (x, y)
            for x in range(self.width)
            for y in range(self.height)
            if (x, y) != tuple(self.agent_pos)
            and (x, y) not in self.walls
            and (x, y) not in self.toxic_traps
        ]
        if self.random_food:
            food_count = min(num_food, len(eligible_food_cells))
            self.food_positions = set(random.sample(eligible_food_cells, food_count))
        else:
            self.food_positions = set(custom_food or ()) & set(eligible_food_cells)

        # Generate adversarial opponents
        self.opponents = []
        while len(self.opponents) < num_opponents:
            ox = random.randint(0, self.width - 1)
            oy = random.randint(0, self.height - 1)
            op_pos = [ox, oy]
            if tuple(op_pos) != tuple(self.agent_pos) and tuple(op_pos) not in self.walls and tuple(op_pos) not in self.food_positions and tuple(op_pos) not in self.toxic_traps:
                self.opponents.append(op_pos)

        self.score = 0
        self.steps = 0
        self.collision = False
        self.last_move_succeeded = True
        self.last_move_result = 'none'

    def get_local_percept(self) -> dict:
        """Return only information available at or directly ahead of the agent."""
        # Declare direction offsets (orthogonally adjacent)
        direction_offsets = {
            'Up': (0, 1),
            'Down': (0, -1),
            'Left': (-1, 0),
            'Right': (1, 0)
        }
        # Determine the cell directly ahead of the agent based on its facing direction
        dx, dy = direction_offsets[self.facing_direction]
        cell_ahead = (self.agent_pos[0] + dx, self.agent_pos[1] + dy)
        outside_grid = not (0 <= cell_ahead[0] < self.width and 0 <= cell_ahead[1] < self.height)

        # Check for food, walls, and toxic traps in the relevant positions
        return {
            'wall_ahead': outside_grid or cell_ahead in self.walls,
            'food_here': tuple(self.agent_pos) in self.food_positions,
            'toxic_trap_ahead': cell_ahead in self.toxic_traps,
            'edge_ahead': outside_grid,
            'last_move_succeeded': self.last_move_succeeded,
            'last_move_result': self.last_move_result
        }

    def get_global_percept(self) -> dict:
        """Return local sensing plus global map information for fully informed agents."""
        percept = self.get_local_percept()
        percept.update({
            'agent_pos': tuple(self.agent_pos),
            'grid_size': (self.width, self.height),
            'walls': list(self.walls),
            'all_toxic_traps': list(self.toxic_traps),
            'all_food': list(self.food_positions)
        })
        return percept

    def execute_action(self, action: str):
        self.steps += 1
        new_pos = list(self.agent_pos)

        if action in ('Up', 'Down', 'Left', 'Right'):
            self.facing_direction = action

        if action == 'Up':
            new_pos[1] = min(self.height - 1, new_pos[1] + 1)
        elif action == 'Down':
            new_pos[1] = max(0, new_pos[1] - 1)
        elif action == 'Left':
            new_pos[0] = max(0, new_pos[0] - 1)
        elif action == 'Right':
            new_pos[0] = min(self.width - 1, new_pos[0] + 1)

        old_pos = list(self.agent_pos)
        if tuple(new_pos) in self.walls:
            self.score -= 5
            self.last_move_succeeded = False
            self.last_move_result = 'wall'
        elif tuple(new_pos) in self.toxic_traps:
            self.score -= 15
            self.last_move_succeeded = False
            self.last_move_result = 'toxic_trap'
        elif action in ('Up', 'Down', 'Left', 'Right') and new_pos == old_pos:
            self.last_move_succeeded = False
            self.last_move_result = 'edge'
        else:
            self.agent_pos = new_pos
            self.last_move_succeeded = True
            self.last_move_result = 'success'

        tuple_pos = tuple(self.agent_pos)
        if tuple_pos in self.food_positions:
            self.food_positions.remove(tuple_pos)
            self.score += 20

        for op in self.opponents:
            move = random.choice(['Up', 'Down', 'Left', 'Right', 'Stay'])
            if move == 'Up' and op[1] < self.height - 1:
                op[1] += 1
            elif move == 'Down' and op[1] > 0:
                op[1] -= 1
            elif move == 'Left' and op[0] > 0:
                op[0] -= 1
            elif move == 'Right' and op[0] < self.width - 1:
                op[0] += 1

            if op == self.agent_pos:
                self.score -= 50
                self.collision = True

    def is_done(self) -> bool:
        reached_step_limit = self.max_steps is not None and self.steps >= self.max_steps
        return len(self.food_positions) == 0 or reached_step_limit or self.collision


class GridGameGUI:
    """Tkinter wrapper that dynamically scales cell sizes to keep larger grids on screen."""

    def __init__(self, root, width=15, height=15, num_food=12, num_opponents=2, walls=None):
        self.root = root
        self.root.title("IT3012 - Scalable Multi-Agent Grid Hunt")

        saved_walls, saved_toxic_traps = load_level_positions()
        saved_start = load_start_position()
        saved_food, self.random_food = load_food_configuration()
        if walls is not None:
            saved_walls = set(walls)

        def is_valid_coordinate(position):
            return len(position) == 2 and position[0] >= 0 and position[1] >= 0

        if not is_valid_coordinate(saved_start) or not (saved_start[0] < width and saved_start[1] < height):
            saved_start = (0, 0)
        self.level_walls = {position for position in saved_walls if is_valid_coordinate(position)}
        self.level_toxic_traps = {
            position for position in saved_toxic_traps if is_valid_coordinate(position)
        } - self.level_walls
        self.level_food = {
            position for position in saved_food if is_valid_coordinate(position)
        } - self.level_walls - self.level_toxic_traps
        visible_walls = {
            position for position in self.level_walls
            if position[0] < width and position[1] < height and position != saved_start
        }
        visible_toxic_traps = {
            position for position in self.level_toxic_traps
            if position[0] < width and position[1] < height and position != saved_start
        }
        visible_food = {
            position for position in self.level_food
            if position[0] < width and position[1] < height and position != saved_start
        }

        available_food_cells = width * height - len(visible_walls | visible_toxic_traps | {saved_start})
        default_food_count = round(available_food_cells * DEFAULT_FOOD_CONCENTRATION / 100)

        self.game_settings = {
            'width': width,
            'height': height,
            'num_food': default_food_count,
            'num_opponents': num_opponents,
            'custom_walls': visible_walls,
            'custom_toxic_traps': visible_toxic_traps,
            'custom_food': visible_food,
            'random_food': self.random_food,
            'start_position': saved_start,
            'max_steps': 150
        }
        self.env = VisualGridHuntGame(**self.game_settings)
        self.agent = SearchAgent()
        self.agent.active_algo = 'AStar'
        self.edit_mode = False
        self.simulation_running = False
        self.scheduled_step = None
        self.last_edited_tile = None
        self.edit_phase = None
        self.pending_start_position = None
        self.start_position_required = False
        self.restart_required = False

        # Keep the canvas fixed while scaling cells to fill it at every grid size.
        self.canvas_size = 600
        self.cell_size = self.canvas_size / max(self.env.width, self.env.height)

        self.canvas = tk.Canvas(root, width=self.canvas_size, height=self.canvas_size, bg="white")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.edit_tile)
        self.canvas.bind("<B1-Motion>", self.edit_tile)
        self.canvas.bind("<ButtonRelease-1>", self.finish_edit_stroke)
        self.canvas.bind("<Leave>", self.leave_canvas)

        self.label = tk.Label(root, text="Score: 0 | Steps: 0", font=("Arial", 14))
        self.label.pack(pady=10)

        self.agent_frame = tk.Frame(root)
        self.agent_frame.pack()
        tk.Label(self.agent_frame, text="Agent:", font=("Arial", 11)).pack(side="left", padx=(0, 4))
        self.agent_choice = tk.StringVar(value="Search Agent (AStar)")
        self.agent_menu = tk.OptionMenu(self.agent_frame, self.agent_choice, *AGENT_TYPES)
        self.agent_menu.config(font=("Arial", 11), width=18)
        self.agent_menu.pack(side="left")

        self.food_frame = tk.Frame(root)
        self.food_frame.pack(pady=4)
        self.food_scale = tk.Scale(self.food_frame, from_=0, to=100, orient="horizontal", resolution=1,
                                   label="Food (%)", length=150)
        self.food_scale.set(DEFAULT_FOOD_CONCENTRATION)
        self.food_scale.pack(side="left", padx=4)
        self.food_scale.bind("<ButtonRelease-1>", self.update_food_concentration)
        self.retry_food_btn = tk.Button(self.food_frame, text="Retry Food",
                                        command=self.regenerate_food, font=("Arial", 11),
                                        bg="#b45309", fg="white")
        self.retry_food_btn.pack(side="left", padx=4)

        self.steps_control = tk.Frame(self.food_frame)
        self.steps_control.pack(side="left", padx=4)
        self.steps_value = tk.StringVar(value="Max steps: 150")
        tk.Label(self.steps_control, textvariable=self.steps_value).pack()
        self.steps_scale = tk.Scale(
            self.steps_control,
            from_=50,
            to=550,
            orient="horizontal",
            resolution=50,
            length=150,
            showvalue=False,
            command=self.update_max_steps
        )
        self.steps_scale.set(150)
        self.steps_scale.pack()

        self.grid_size_frame = tk.Frame(root)
        self.grid_size_scale = tk.Scale(
            self.grid_size_frame,
            from_=7,
            to=15,
            orient="horizontal",
            resolution=1,
            label="Grid size",
            length=180,
            command=self.resize_grid
        )
        self.grid_size_scale.set(width)
        self.grid_size_scale.pack()

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=5)

        self.btn = tk.Button(self.button_frame, text="Start Simulation", command=self.run_loop, font=("Arial", 12),
                             bg="#000066", fg="white")
        self.btn.pack(side="left", padx=4)

        self.edit_btn = tk.Button(self.button_frame, text="Edit Grid", command=self.toggle_edit_mode,
                                  font=("Arial", 12), bg="#475569", fg="white")
        self.edit_btn.pack(side="left", padx=4)

        self.clear_btn = tk.Button(self.button_frame, text="Clear Grid", command=self.clear_grid,
                                   font=("Arial", 12), bg="#b91c1c", fg="white")

        self.draw_grid()

    def available_food_cell_count(self):
        occupied = set(self.game_settings['custom_walls']) | set(self.game_settings['custom_toxic_traps'])
        occupied.add(tuple(self.game_settings['start_position']))
        return self.game_settings['width'] * self.game_settings['height'] - len(occupied)

    def food_count_for_concentration(self):
        return round(self.available_food_cell_count() * self.food_scale.get() / 100)

    def update_food_concentration(self, _event):
        self.game_settings['num_food'] = self.food_count_for_concentration()
        if self.random_food:
            self.regenerate_food(set_random=False)

    def update_max_steps(self, value):
        slider_value = int(float(value))
        max_steps = None if slider_value > 500 else slider_value
        self.game_settings['max_steps'] = max_steps
        self.env.max_steps = max_steps
        display_value = "Infinite" if max_steps is None else str(max_steps)
        self.steps_value.set(f"Max steps: {display_value}")

    def _position_in_grid(self, position):
        return (
            0 <= position[0] < self.game_settings['width']
            and 0 <= position[1] < self.game_settings['height']
        )

    def _sync_visible_terrain(self):
        """Merge visible edits into the full level without deleting hidden coordinates."""
        width = self.game_settings['width']
        height = self.game_settings['height']
        self.level_walls = {
            position for position in self.level_walls
            if not (0 <= position[0] < width and 0 <= position[1] < height)
        } | set(self.env.walls)
        self.level_toxic_traps = {
            position for position in self.level_toxic_traps
            if not (0 <= position[0] < width and 0 <= position[1] < height)
        } | set(self.env.toxic_traps)
        self.level_toxic_traps -= self.level_walls
        self.level_food = {
            position for position in self.level_food
            if not (0 <= position[0] < width and 0 <= position[1] < height)
        } | set(self.env.food_positions)
        self.level_food -= self.level_walls | self.level_toxic_traps

    def _visible_terrain(self):
        return (
            {position for position in self.level_walls if self._position_in_grid(position)},
            {position for position in self.level_toxic_traps if self._position_in_grid(position)},
            {position for position in self.level_food if self._position_in_grid(position)}
        )

    def resize_grid(self, value):
        if not self.edit_mode or self.edit_phase != 'terrain':
            return

        self._sync_visible_terrain()
        size = int(float(value))
        self.game_settings['width'] = size
        self.game_settings['height'] = size
        visible_walls, visible_traps, visible_food = self._visible_terrain()
        self.game_settings['custom_walls'] = visible_walls
        self.game_settings['custom_toxic_traps'] = visible_traps
        self.game_settings['custom_food'] = visible_food
        self.game_settings['random_food'] = 0
        self.env = VisualGridHuntGame(**self.game_settings)
        if self.random_food:
            self.env.food_positions.clear()
        self.cell_size = self.canvas_size / size
        self.last_edited_tile = None
        self.label.config(text=f"Edit mode: {size}×{size} grid")
        self.draw_grid()

    def regenerate_food(self, set_random=True):
        if self.edit_mode or self.simulation_running:
            return
        if set_random:
            self.random_food = 1
            self.level_food.clear()
        self.game_settings['random_food'] = 1
        self.game_settings['custom_food'] = set()
        self.game_settings['num_food'] = self.food_count_for_concentration()
        self.env = VisualGridHuntGame(**self.game_settings)
        save_level_positions(
            self.level_walls,
            self.level_toxic_traps,
            self.game_settings['start_position'],
            set(),
            1
        )
        self.restart_required = False
        self.btn.config(text="Start Simulation", state="normal", bg="#000066")
        self.label.config(text=f"Food regenerated | Food: {len(self.env.food_positions)} | Score: 0 | Steps: 0")
        self.draw_grid()

    def toggle_edit_mode(self):
        if not self.edit_mode:
            self.edit_mode = True
            self.edit_phase = 'terrain'
            self.pending_start_position = None
            self.start_position_required = False
            self.env = VisualGridHuntGame(**self.game_settings)
            if self.random_food:
                self.env.food_positions.clear()
                self.level_food = {
                    position for position in self.level_food if not self._position_in_grid(position)
                }
            self.food_frame.pack_forget()
            self.grid_size_frame.pack(pady=4, before=self.button_frame)
            self.grid_size_scale.config(state="normal")
            self.grid_size_scale.set(self.game_settings['width'])
            self.btn.config(state="disabled")
            self.agent_menu.config(state="disabled")
            self.retry_food_btn.config(state="disabled")
            self.steps_scale.config(state="disabled")
            self.edit_btn.config(text="Save Changes", bg="#15803d")
            self.clear_btn.pack(side="left", padx=4)
            self.label.config(text="Edit mode: cycle Empty → Wall → Toxic Trap → Food")
            self.draw_grid()
            return

        if self.edit_phase == 'terrain':
            self._sync_visible_terrain()
            self.random_food = 0 if self.env.food_positions else 1
            save_level_positions(
                self.level_walls,
                self.level_toxic_traps,
                food_positions=self.level_food,
                random_food=self.random_food
            )
            visible_walls, visible_traps, visible_food = self._visible_terrain()
            self.game_settings['custom_walls'] = visible_walls
            self.game_settings['custom_toxic_traps'] = visible_traps
            self.game_settings['custom_food'] = visible_food
            self.game_settings['random_food'] = self.random_food
            self.edit_phase = 'start'
            self.last_edited_tile = None
            self.grid_size_scale.config(state="disabled")
            original_start = tuple(self.game_settings['start_position'])
            self.start_position_required = (
                not self._position_in_grid(original_start)
                or original_start in self.env.walls
                or original_start in self.env.toxic_traps
                or original_start in self.env.food_positions
            )
            self.edit_btn.config(text="Set Start Position")
            self.clear_btn.pack_forget()
            if self.start_position_required:
                self.label.config(text="The previous start is blocked — select a new blank start tile")
            else:
                self.label.config(text="Select a blank start tile, or press Set Start Position to keep the current one")
            self.draw_grid()
            return

        if self.start_position_required and self.pending_start_position is None:
            self.label.config(text="Select a blank start tile before continuing")
            return

        start_position = self.pending_start_position or tuple(self.env.agent_pos)
        save_level_positions(
            self.level_walls,
            self.level_toxic_traps,
            start_position,
            self.level_food,
            self.random_food
        )
        self.game_settings['start_position'] = start_position
        self.game_settings['random_food'] = self.random_food
        self.game_settings['custom_food'] = {
            position for position in self.level_food if self._position_in_grid(position)
        }
        self.game_settings['num_food'] = self.food_count_for_concentration()
        self.env = VisualGridHuntGame(**self.game_settings)
        self.edit_mode = False
        self.edit_phase = None
        self.pending_start_position = None
        self.start_position_required = False
        self.restart_required = False
        self.btn.config(text="Start Simulation", state="normal")
        self.agent_menu.config(state="normal")
        self.retry_food_btn.config(state="normal")
        self.steps_scale.config(state="normal")
        self.grid_size_frame.pack_forget()
        self.food_frame.pack(pady=4, before=self.button_frame)
        self.edit_btn.config(text="Edit Grid", bg="#475569")
        self.clear_btn.pack_forget()
        self.label.config(text="Changes saved | Score: 0 | Steps: 0")
        self.draw_grid()

    def clear_grid(self):
        if not self.edit_mode or self.edit_phase != 'terrain':
            return
        if not messagebox.askyesno(
                "Clear Grid",
                "Clear all walls, toxic traps, and preset food from the grid?"
        ):
            return
        if not messagebox.askyesno(
                "Confirm Clear Grid",
                "Are you sure? This will remove every wall, toxic trap, and food tile."
        ):
            return

        self.env.walls.clear()
        self.env.toxic_traps.clear()
        self.env.food_positions.clear()
        self.last_edited_tile = None
        self.label.config(text="Grid cleared — click Save Changes to save")
        self.draw_grid()

    def edit_tile(self, event):
        if not self.edit_mode:
            return

        x = int(event.x // self.cell_size)
        y = self.env.height - 1 - int(event.y // self.cell_size)
        position = (x, y)
        if not (0 <= x < self.env.width and 0 <= y < self.env.height):
            self.last_edited_tile = None
            return
        if position == self.last_edited_tile:
            return

        self.last_edited_tile = position

        if self.edit_phase == 'start':
            if (position not in self.env.walls and position not in self.env.toxic_traps
                    and position not in self.env.food_positions):
                self.pending_start_position = position
                self.start_position_required = False
                self.label.config(text=f"Selected start tile: {position} — press Set Start Position")
                self.draw_grid()
            return

        if position in self.env.walls:
            self.env.walls.remove(position)
            self.env.toxic_traps.add(position)
        elif position in self.env.toxic_traps:
            self.env.toxic_traps.remove(position)
            self.env.food_positions.add(position)
        elif position in self.env.food_positions:
            self.env.food_positions.remove(position)
        else:
            self.env.walls.add(position)
        self.draw_grid()

    def finish_edit_stroke(self, _event):
        self.last_edited_tile = None

    def leave_canvas(self, _event):
        if self.edit_mode:
            self.last_edited_tile = None

    def draw_grid(self):
        self.canvas.delete("all")

        for x in range(self.env.width):
            for y in range(self.env.height):
                x1 = x * self.cell_size
                y1 = (self.env.height - 1 - y) * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                color = "#f1f5f9" if (x, y) not in self.env.walls else "#64748b"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#cbd5e1", width=1)

                # Only draw text if cell is large enough
                if self.cell_size >= 40 and (x, y) in self.env.walls:
                    self.canvas.create_text(x1 + self.cell_size / 2, y1 + self.cell_size / 2, text="", fill="white",
                                            font=("Arial", 12, "bold"))

        for fx, fy in self.env.food_positions:
            offset = self.cell_size * 0.25
            x1 = fx * self.cell_size + offset
            y1 = (self.env.height - 1 - fy) * self.cell_size + offset
            self.canvas.create_oval(x1, y1, x1 + self.cell_size * 0.5, y1 + self.cell_size * 0.5, fill="#f59e0b",
                                    outline="#d97706", width=3)

        for tx, ty in self.env.toxic_traps:
            offset = self.cell_size * 0.25
            x1 = tx * self.cell_size + offset
            y1 = (self.env.height - 1 - ty) * self.cell_size + offset
            self.canvas.create_polygon(
                x1 + self.cell_size * 0.25, y1,
                x1, y1 + self.cell_size * 0.5,
                x1 + self.cell_size * 0.5, y1 + self.cell_size * 0.5,
                fill="#ad14c1",
                outline="#830c92",
                width=3
            )

        for ox, oy in self.env.opponents:
            offset = self.cell_size * 0.2
            x1 = ox * self.cell_size + offset
            y1 = (self.env.height - 1 - oy) * self.cell_size + offset
            self.canvas.create_rectangle(x1, y1, x1 + self.cell_size * 0.6, y1 + self.cell_size * 0.6, fill="#990000",
                                         outline="#7a0000")

        show_agent = not self.edit_mode or (
            self.edit_phase == 'start' and
            (self.pending_start_position is not None or not self.start_position_required)
        )
        if show_agent:
            if self.edit_phase == 'start' and self.pending_start_position is not None:
                ax, ay = self.pending_start_position
            else:
                ax, ay = self.env.agent_pos
            offset = self.cell_size * 0.15
            x1 = ax * self.cell_size + offset
            y1 = (self.env.height - 1 - ay) * self.cell_size + offset
            self.canvas.create_oval(x1, y1, x1 + self.cell_size * 0.7, y1 + self.cell_size * 0.7,
                                    fill="#000066", outline="#1e3a8a")

    def create_selected_agent(self):
        agent_class, algorithm = AGENT_TYPES[self.agent_choice.get()]
        agent = agent_class()
        if isinstance(agent, SearchAgent):
            agent.active_algo = algorithm
        return agent

    def run_loop(self):
        if self.edit_mode:
            return

        if self.simulation_running:
            self.stop_simulation()
            return

        if self.env.is_done() or self.restart_required:
            self.reset_simulation()
            return

        self.agent = self.create_selected_agent()
        if isinstance(self.agent, ModelBasedAgent):
            self.agent.facing_direction = self.env.facing_direction
        self.simulation_running = True
        self.btn.config(text="Stop Simulation", state="normal", bg="#b91c1c")
        self.agent_menu.config(state="disabled")
        self.retry_food_btn.config(state="disabled")
        self.steps_scale.config(state="disabled")
        self.edit_btn.config(state="disabled")

        def step():
            if self.simulation_running and not self.env.is_done():
                if isinstance(self.agent, SearchAgent):
                    percept = self.env.get_global_percept()
                else:
                    percept = self.env.get_local_percept()
                action = self.agent.sense_and_act(percept)
                self.env.execute_action(action)

                self.draw_grid()
                self.label.config(text=f"Score: {self.env.score} | Steps: {self.env.steps} | Action: {action}")
                self.scheduled_step = self.root.after(250, step)
            elif self.simulation_running:
                self.simulation_running = False
                self.scheduled_step = None
                self.restart_required = True
                self.label.config(text=f"Finished! Final Score: {self.env.score} | Steps: {self.env.steps}")
                self.btn.config(text="Reset Simulation", state="normal", bg="#000066")
                self.agent_menu.config(state="normal")
                self.retry_food_btn.config(state="normal")
                self.steps_scale.config(state="normal")
                self.edit_btn.config(state="normal")

        step()

    def reset_simulation(self):
        """Restore initial state without starting the simulation."""
        self.env = VisualGridHuntGame(**self.game_settings)
        self.agent = self.create_selected_agent()
        if isinstance(self.agent, ModelBasedAgent):
            self.agent.facing_direction = self.env.facing_direction
        self.simulation_running = False
        self.restart_required = False
        self.scheduled_step = None
        self.draw_grid()
        self.label.config(text="Reset complete | Score: 0 | Steps: 0")
        self.btn.config(text="Start Simulation", state="normal", bg="#000066")
        self.agent_menu.config(state="normal")
        self.retry_food_btn.config(state="normal")
        self.steps_scale.config(state="normal")
        self.edit_btn.config(state="normal")

    def stop_simulation(self):
        self.simulation_running = False
        self.restart_required = True
        if self.scheduled_step is not None:
            self.root.after_cancel(self.scheduled_step)
            self.scheduled_step = None
        self.btn.config(text="Reset Simulation", state="normal", bg="#000066")
        self.agent_menu.config(state="normal")
        self.retry_food_btn.config(state="normal")
        self.steps_scale.config(state="normal")
        self.edit_btn.config(state="normal")
        self.label.config(text=f"Simulation stopped | Final Score: {self.env.score} | Steps: {self.env.steps}")


if __name__ == "__main__":
    root = tk.Tk()
    app = GridGameGUI(root, width=15, height=15, num_food=15, num_opponents=0)
    root.mainloop()
