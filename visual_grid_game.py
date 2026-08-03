# visual_grid_game.py
import json
import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from agent import GreedyGridAgent, ModelBasedAgent, SimpleReflexAgent


LEVEL_FILE = Path(__file__).with_name("level_positions.json")
AGENT_TYPES = {
    "Greedy Grid Agent": GreedyGridAgent,
    "Simple Reflex Agent": SimpleReflexAgent,
    "Model-Based Agent": ModelBasedAgent
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


def save_level_positions(walls, toxic_traps, player_start=None, level_file=LEVEL_FILE):
    """Persist terrain coordinates in a readable, stable order."""
    if player_start is None:
        player_start = load_start_position(level_file)
    level = {
        "walls": [list(position) for position in sorted(walls)],
        "toxic_traps": [list(position) for position in sorted(toxic_traps)],
        "player_start": list(player_start)
    }
    with open(level_file, "w", encoding="utf-8") as file:
        json.dump(level, file, indent=2)
        file.write("\n")

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

    def __init__(self, width=10, height=10, num_food=10, num_opponents=2, custom_walls=None,
                 custom_toxic_traps=None, start_position=(0, 0)):
        self.width = width
        self.height = height
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

        # Dynamically generate random food positions avoiding walls, toxic traps, and agent start
        self.food_positions = set()
        while len(self.food_positions) < num_food:
            fx = random.randint(0, self.width - 1)
            fy = random.randint(0, self.height - 1)
            pos_tuple = (fx, fy)
            if pos_tuple != tuple(self.agent_pos) and pos_tuple not in self.walls and pos_tuple not in self.toxic_traps:
                self.food_positions.add(pos_tuple)

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

    def get_percept(self) -> dict:
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
            'toxic_trap_ahead': outside_grid or cell_ahead in self.toxic_traps,
            'last_move_succeeded': self.last_move_succeeded
        }

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
        elif tuple(new_pos) in self.toxic_traps:
            self.score -= 15
            self.last_move_succeeded = False
        else:
            self.agent_pos = new_pos
            self.last_move_succeeded = action not in ('Up', 'Down', 'Left', 'Right') or new_pos != old_pos

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
        return len(self.food_positions) == 0 or self.steps >= 100 or self.collision


class GridGameGUI:
    """Tkinter wrapper that dynamically scales cell sizes to keep larger grids on screen."""

    def __init__(self, root, width=10, height=10, num_food=12, num_opponents=2, walls=None):
        self.root = root
        self.root.title("IT3012 - Scalable Multi-Agent Grid Hunt")

        saved_walls, saved_toxic_traps = load_level_positions()
        saved_start = load_start_position()
        if walls is not None:
            saved_walls = set(walls)

        def is_valid_tile(position):
            return len(position) == 2 and 0 <= position[0] < width and 0 <= position[1] < height

        if not is_valid_tile(saved_start):
            saved_start = (0, 0)
        saved_walls = {position for position in saved_walls if is_valid_tile(position) and position != saved_start}
        saved_toxic_traps = {position for position in saved_toxic_traps if is_valid_tile(position)} - saved_walls
        saved_toxic_traps.discard(saved_start)

        self.game_settings = {
            'width': width,
            'height': height,
            'num_food': num_food,
            'num_opponents': num_opponents,
            'custom_walls': saved_walls,
            'custom_toxic_traps': saved_toxic_traps,
            'start_position': saved_start
        }
        self.env = VisualGridHuntGame(**self.game_settings)
        self.agent = ModelBasedAgent()
        self.edit_mode = False
        self.simulation_running = False
        self.scheduled_step = None
        self.last_edited_tile = None
        self.edit_phase = None
        self.pending_start_position = None
        self.start_position_required = False
        self.restart_required = False

        # Dynamically calculate cell size so the total canvas fits nicely within a 600x600 window ceiling
        max_canvas_dim = 600
        self.cell_size = max(20, min(max_canvas_dim // self.env.width, max_canvas_dim // self.env.height))

        canvas_w = self.env.width * self.cell_size
        canvas_h = self.env.height * self.cell_size

        self.canvas = tk.Canvas(root, width=canvas_w, height=canvas_h, bg="white")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.edit_tile)
        self.canvas.bind("<B1-Motion>", self.edit_tile)
        self.canvas.bind("<ButtonRelease-1>", self.finish_edit_stroke)
        self.canvas.bind("<Leave>", self.leave_canvas)

        self.label = tk.Label(root, text="Score: 0 | Steps: 0", font=("Arial", 14))
        self.label.pack(pady=10)

        agent_frame = tk.Frame(root)
        agent_frame.pack()
        tk.Label(agent_frame, text="Agent:", font=("Arial", 11)).pack(side="left", padx=(0, 4))
        self.agent_choice = tk.StringVar(value="Model-Based Agent")
        self.agent_menu = tk.OptionMenu(agent_frame, self.agent_choice, *AGENT_TYPES)
        self.agent_menu.config(font=("Arial", 11), width=18)
        self.agent_menu.pack(side="left")

        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        self.btn = tk.Button(button_frame, text="Start Simulation", command=self.run_loop, font=("Arial", 12),
                             bg="#000066", fg="white")
        self.btn.pack(side="left", padx=4)

        self.edit_btn = tk.Button(button_frame, text="Edit Grid", command=self.toggle_edit_mode,
                                  font=("Arial", 12), bg="#475569", fg="white")
        self.edit_btn.pack(side="left", padx=4)

        self.clear_btn = tk.Button(button_frame, text="Clear Grid", command=self.clear_grid,
                                   font=("Arial", 12), bg="#b91c1c", fg="white")

        self.draw_grid()

    def toggle_edit_mode(self):
        if not self.edit_mode:
            self.edit_mode = True
            self.edit_phase = 'terrain'
            self.pending_start_position = None
            self.start_position_required = False
            self.env = VisualGridHuntGame(**self.game_settings)
            self.env.food_positions.clear()
            self.btn.config(state="disabled")
            self.agent_menu.config(state="disabled")
            self.edit_btn.config(text="Save Changes", bg="#15803d")
            self.clear_btn.pack(side="left", padx=4)
            self.label.config(text="Edit mode: click a tile to cycle Empty → Wall → Toxic Trap")
            self.draw_grid()
            return

        if self.edit_phase == 'terrain':
            save_level_positions(self.env.walls, self.env.toxic_traps)
            self.game_settings['custom_walls'] = set(self.env.walls)
            self.game_settings['custom_toxic_traps'] = set(self.env.toxic_traps)
            self.edit_phase = 'start'
            self.last_edited_tile = None
            original_start = tuple(self.game_settings['start_position'])
            self.start_position_required = (
                original_start in self.env.walls or original_start in self.env.toxic_traps
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
        save_level_positions(self.env.walls, self.env.toxic_traps, start_position)
        self.game_settings['start_position'] = start_position
        self.env = VisualGridHuntGame(**self.game_settings)
        self.edit_mode = False
        self.edit_phase = None
        self.pending_start_position = None
        self.start_position_required = False
        self.restart_required = False
        self.btn.config(text="Start Simulation", state="normal")
        self.agent_menu.config(state="normal")
        self.edit_btn.config(text="Edit Grid", bg="#475569")
        self.clear_btn.pack_forget()
        self.label.config(text="Changes saved | Score: 0 | Steps: 0")
        self.draw_grid()

    def clear_grid(self):
        if not self.edit_mode or self.edit_phase != 'terrain':
            return
        if not messagebox.askyesno(
                "Clear Grid",
                "Clear all walls and toxic traps from the grid?"
        ):
            return
        if not messagebox.askyesno(
                "Confirm Clear Grid",
                "Are you sure? This will remove every wall and toxic trap."
        ):
            return

        self.env.walls.clear()
        self.env.toxic_traps.clear()
        self.last_edited_tile = None
        self.label.config(text="Grid cleared — click Save Changes to save")
        self.draw_grid()

    def edit_tile(self, event):
        if not self.edit_mode:
            return

        x = event.x // self.cell_size
        y = self.env.height - 1 - (event.y // self.cell_size)
        position = (x, y)
        if not (0 <= x < self.env.width and 0 <= y < self.env.height):
            self.last_edited_tile = None
            return
        if position == self.last_edited_tile:
            return

        self.last_edited_tile = position

        if self.edit_phase == 'start':
            if position not in self.env.walls and position not in self.env.toxic_traps:
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
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#cbd5e1", width=2)

                # Only draw text if cell is large enough
                if self.cell_size >= 40 and (x, y) in self.env.walls:
                    self.canvas.create_text(x1 + self.cell_size / 2, y1 + self.cell_size / 2, text="W", fill="white",
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

    def run_loop(self):
        if self.edit_mode:
            return

        if self.simulation_running:
            self.stop_simulation()
            return

        if self.env.is_done() or self.restart_required:
            self.env = VisualGridHuntGame(**self.game_settings)
            self.restart_required = False
            self.draw_grid()
            self.label.config(text="Score: 0 | Steps: 0")

        self.agent = AGENT_TYPES[self.agent_choice.get()]()
        if isinstance(self.agent, ModelBasedAgent):
            self.agent.facing_direction = self.env.facing_direction
        self.simulation_running = True
        self.btn.config(text="Stop Simulation", state="normal", bg="#b91c1c")
        self.agent_menu.config(state="disabled")
        self.edit_btn.config(state="disabled")

        def step():
            if self.simulation_running and not self.env.is_done():
                percept = self.env.get_percept()
                action = self.agent.sense_and_act(percept)
                self.env.execute_action(action)

                self.draw_grid()
                self.label.config(text=f"Score: {self.env.score} | Steps: {self.env.steps} | Action: {action}")
                self.scheduled_step = self.root.after(250, step)
            elif self.simulation_running:
                self.simulation_running = False
                self.scheduled_step = None
                end_text = f"Collision! Game Over! Final Score: {self.env.score}" if self.env.collision else f"Finished! Final Score: {self.env.score}"
                self.label.config(text=end_text)
                self.btn.config(text="Restart Simulation", state="normal", bg="#000066")
                self.agent_menu.config(state="normal")
                self.edit_btn.config(state="normal")

        step()

    def stop_simulation(self):
        self.simulation_running = False
        self.restart_required = True
        if self.scheduled_step is not None:
            self.root.after_cancel(self.scheduled_step)
            self.scheduled_step = None
        self.btn.config(text="Restart Simulation", state="normal", bg="#000066")
        self.agent_menu.config(state="normal")
        self.edit_btn.config(state="normal")
        self.label.config(text=f"Simulation stopped | Score: {self.env.score} | Steps: {self.env.steps}")


if __name__ == "__main__":
    root = tk.Tk()
    # Try a larger grid size like 12x12 with 15 food and 3 opponents!
    app = GridGameGUI(root, width=12, height=12, num_food=15, num_opponents=0)
    root.mainloop()
