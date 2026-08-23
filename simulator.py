# simulator.py
from agent import SimpleReflexAgent
from visual_grid_game import (
    VisualGridHuntGame,
    load_food_configuration,
    load_level_positions,
    load_start_position,
)


def run_grid_hunt(width=15, height=15, num_food=15):
    walls, toxic_traps = load_level_positions()
    food_positions, random_food = load_food_configuration()
    start_position = load_start_position()
    if not (0 <= start_position[0] < width and 0 <= start_position[1] < height):
        start_position = (0, 0)
    walls = {position for position in walls if 0 <= position[0] < width and 0 <= position[1] < height}
    toxic_traps = {
        position for position in toxic_traps
        if 0 <= position[0] < width and 0 <= position[1] < height
    } - walls
    walls.discard(start_position)
    toxic_traps.discard(start_position)
    food_positions = {
        position for position in food_positions
        if 0 <= position[0] < width and 0 <= position[1] < height
    } - walls - toxic_traps - {start_position}

    env = VisualGridHuntGame(
        width=width,
        height=height,
        num_food=num_food,
        num_opponents=0,
        custom_walls=walls,
        custom_toxic_traps=toxic_traps,
        custom_food=food_positions,
        random_food=random_food,
        start_position=start_position
    )
    agent = SimpleReflexAgent()

    print("=== Simple Reflex Agent Grid Hunt Started ===")
    while not env.is_done():
        percept = env.get_local_percept()
        action = agent.sense_and_act(percept)
        env.execute_action(action)
        print(
            f"Step: {env.steps} | Percept: {percept} | "
            f"Action: {action} | Food Left: {len(env.food_positions)} | Score: {env.score}"
        )

    print(f"\nGame Over! Final Score: {env.score} after {env.steps} steps.")

if __name__ == "__main__":
    run_grid_hunt()
