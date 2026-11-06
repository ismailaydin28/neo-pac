"""Pre-train all four NeoPac Q-learning personalities.

Usage: python train_ai.py --episodes 500
The resulting ai_memory.json is also refined continuously during real play.
"""

import argparse
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from learning_ai import ACTION_DELTAS, load_brains, save_brains
from maze import Maze


def nearest_open(maze, target, passable):
    tr = max(0, min(len(maze.tiles) - 1, target[0]))
    tc = max(0, min(len(maze.tiles[0]) - 1, target[1]))
    if not maze.is_wall_at(tr, tc):
        return (tr, tc)
    return min(passable, key=lambda tile: abs(tile[0] - tr) + abs(tile[1] - tc))


def personality_target(index, player, player_direction):
    pr, pc = player
    dr, dc = player_direction
    if index == 0:                       # chaser
        return player
    if index == 1:                       # ambusher
        return (pr + dr * 4, pc + dc * 4)
    if index == 2:                       # flanker
        return (pr - dc * 4, pc + dr * 4)
    return player                        # explorer stays near the action


def shaped_reward(index, before, after, is_new):
    improvement = before - after
    if index == 0:
        return improvement * 1.7 + (0.45 if after <= 2 else -0.03)
    if index == 1:
        return improvement * 1.45 + (0.65 if after <= 3 else -0.02)
    if index == 2:
        return improvement * 1.3 + (0.55 if after <= 2 else -0.02)
    return (0.85 if is_new else -0.18) + improvement * 0.12


def train(episodes, steps_per_episode, seed):
    rng = random.Random(seed)
    brains = load_brains()
    for personality, brain in enumerate(brains):
        for episode in range(episodes):
            maze = Maze(seed=seed + personality * 100_000 + episode)
            passable = [
                (r, c)
                for r, row in enumerate(maze.tiles)
                for c, _ in enumerate(row)
                if not maze.is_wall_at(r, c)
            ]
            position = rng.choice(passable)
            player = rng.choice(passable)
            heading = rng.choice(ACTION_DELTAS)
            player_direction = rng.choice(ACTION_DELTAS)
            visited = {position}

            for step in range(steps_per_episode):
                target = nearest_open(
                    maze,
                    personality_target(personality, player, player_direction),
                    passable,
                )
                legal = [
                    action for action, (dr, dc) in enumerate(ACTION_DELTAS)
                    if not maze.is_wall_at(position[0] + dr, position[1] + dc)
                ]
                state = brain.encode_state(
                    maze, position, target, (heading[1], heading[0]), "chase"
                )
                heuristic = min(
                    legal,
                    key=lambda action: abs(position[0] + ACTION_DELTAS[action][0] - target[0])
                    + abs(position[1] + ACTION_DELTAS[action][1] - target[1]),
                )
                action = brain.choose_action(state, legal, heuristic, epsilon=0.28)
                dr, dc = ACTION_DELTAS[action]
                next_position = (position[0] + dr, position[1] + dc)
                before = abs(position[0] - target[0]) + abs(position[1] - target[1])
                after = abs(next_position[0] - target[0]) + abs(next_position[1] - target[1])
                reward = shaped_reward(
                    personality, before, after, next_position not in visited
                )
                if next_position == player:
                    reward += 25.0
                    player = rng.choice(passable)
                    player_direction = rng.choice(ACTION_DELTAS)

                next_legal = [
                    next_action
                    for next_action, (ndr, ndc) in enumerate(ACTION_DELTAS)
                    if not maze.is_wall_at(next_position[0] + ndr,
                                           next_position[1] + ndc)
                ]
                next_target = nearest_open(
                    maze,
                    personality_target(personality, player, player_direction),
                    passable,
                )
                next_state = brain.encode_state(
                    maze, next_position, next_target, (dc, dr), "chase"
                )
                brain.update(state, action, reward, next_state, next_legal)
                position = next_position
                heading = (dr, dc)
                visited.add(position)

                if step % 7 == 6:
                    player_moves = [
                        delta for delta in ACTION_DELTAS
                        if not maze.is_wall_at(player[0] + delta[0],
                                               player[1] + delta[1])
                    ]
                    if player_moves:
                        player_direction = rng.choice(player_moves)
                        player = (player[0] + player_direction[0],
                                  player[1] + player_direction[1])

        print(f"{personality}: {brain.steps} learning updates, {len(brain.q)} states")
    save_brains(brains)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--steps", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20261106)
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1, 1))
    train(max(1, args.episodes), max(10, args.steps), args.seed)
    pygame.quit()


if __name__ == "__main__":
    main()
