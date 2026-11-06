"""Small persistent Q-learning brains for NeoPac sentinels.

The state is deliberately compact and maze-independent: nearby walls, target
direction/distance, current heading and behaviour mode. This lets policies
trained on one procedural maze transfer to every later maze without requiring
heavy machine-learning libraries.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from settings import AI_DISCOUNT, AI_EXPLORATION, AI_LEARNING_RATE


ACTION_DELTAS = ((0, -1), (0, 1), (-1, 0), (1, 0))  # left, right, up, down
PERSONALITY_NAMES = ("chaser", "ambusher", "flanker", "explorer")
MEMORY_FILE = Path(__file__).resolve().parent / "ai_memory.json"


class LearningBrain:
    def __init__(self, personality: int, q_table=None, steps=0):
        self.personality = personality % 4
        self.q = q_table or {}
        self.steps = int(steps)

    def encode_state(self, maze, position, target, direction, mode="chase"):
        r, c = position
        tr, tc = target
        walls = 0
        for action, (dr, dc) in enumerate(ACTION_DELTAS):
            if maze.is_wall_at(r + dr, c + dc):
                walls |= 1 << action
        rel_r = -1 if tr < r else (1 if tr > r else 0)
        rel_c = -1 if tc < c else (1 if tc > c else 0)
        distance = min(4, (abs(tr - r) + abs(tc - c)) // 4)
        try:
            heading = ACTION_DELTAS.index((direction[1], direction[0]))
        except ValueError:
            heading = 4
        return f"{walls:x}|{rel_r + 1}{rel_c + 1}|{distance}|{heading}|{mode[:1]}"

    def choose_action(self, state, legal_actions, heuristic_action=None,
                      epsilon=AI_EXPLORATION):
        if not legal_actions:
            return None
        if random.random() < epsilon:
            return random.choice(legal_actions)
        values = self.q.setdefault(state, [0.0, 0.0, 0.0, 0.0])
        scores = {
            action: values[action] + (0.22 if action == heuristic_action else 0.0)
            for action in legal_actions
        }
        best = max(scores.values())
        return random.choice([action for action, value in scores.items()
                              if abs(value - best) < 1e-9])

    def update(self, state, action, reward, next_state=None, next_legal=None):
        if state is None or action is None:
            return
        values = self.q.setdefault(state, [0.0, 0.0, 0.0, 0.0])
        future = 0.0
        if next_state is not None and next_legal:
            next_values = self.q.setdefault(next_state, [0.0, 0.0, 0.0, 0.0])
            future = max(next_values[a] for a in next_legal)
        target = reward + AI_DISCOUNT * future
        values[action] += AI_LEARNING_RATE * (target - values[action])
        self.steps += 1

    def apply_event_reward(self, state, action, reward):
        """Apply immediate catch/eaten rewards to the most recent decision."""
        self.update(state, action, reward)

    def to_dict(self):
        return {
            "name": PERSONALITY_NAMES[self.personality],
            "steps": self.steps,
            "q": self.q,
        }


def load_brains(path=MEMORY_FILE):
    data = {}
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        data = {}
    brains = []
    stored = data.get("brains", {})
    for index in range(4):
        item = stored.get(str(index), {})
        brains.append(LearningBrain(index, item.get("q", {}), item.get("steps", 0)))
    return brains


def save_brains(brains, path=MEMORY_FILE):
    payload = {
        "version": 1,
        "algorithm": "tabular-q-learning",
        "brains": {str(i): brain.to_dict() for i, brain in enumerate(brains)},
    }
    try:
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
        temp.replace(path)
        return True
    except OSError:
        return False


def snapshot_brains(brains):
    """Copy mutable Q tables before a background save starts.

    The live game can keep learning while the copied tables are serialized on
    another thread.  Copying the compact tables is much cheaper than encoding
    and writing the whole JSON file on the render thread.
    """
    return [
        LearningBrain(
            brain.personality,
            {state: list(values) for state, values in brain.q.items()},
            brain.steps,
        )
        for brain in brains
    ]


def action_for_step(position, next_tile):
    delta = (next_tile[0] - position[0], next_tile[1] - position[1])
    try:
        return ACTION_DELTAS.index(delta)
    except ValueError:
        return None
