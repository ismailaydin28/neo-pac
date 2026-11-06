# enemy.py — NeoPac AI Sentinels (hologram drones)

import pygame
import math
import random
from collections import deque
from settings import *
from learning_ai import ACTION_DELTAS, LearningBrain, action_for_step
from sentinel_abilities import SentinelAbility


class Enemy:
    """
    Grid-aligned enemy with three behaviour modes:
      SCATTER  — patrol a fixed corner
      CHASE    — pursue player (simple BFS pathfinding)
      SCARED   — flee (reverse direction, slower)

    Four sentinel personalities determined by index:
      0 = Chaser  (always goes toward player)
      1 = Ambusher (targets 4 tiles ahead of player)
      2 = Flanker (mirrors opposite quadrant)
      3 = Random  (random walk with mild bias toward player)
    """

    MODE_SCATTER = "scatter"
    MODE_CHASE   = "chase"
    MODE_SCARED  = "scared"
    MODE_RESPAWNING = "respawning"

    _glow_cache = {}

    # Corner scatter targets per personality
    SCATTER_TARGETS = [
        (1, COLS - 2),    # top-right
        (1, 1),           # top-left
        (ROWS - 2, COLS - 2),  # bottom-right
        (ROWS - 2, 1),    # bottom-left
    ]

    def __init__(self, index: int, maze, brain=None):
        self.index = index
        self.maze  = maze
        self.color = ENEMY_COLORS[index % len(ENEMY_COLORS)]
        self.personality = index   # 0–3
        self.brain = brain or LearningBrain(self.personality)
        self.ability = SentinelAbility(self.personality)
        self.exploration_scale = 1.0
        self.reset()

    def reset(self):
        spawns = self.maze.enemy_spawns
        self.tile_r, self.tile_c = spawns[self.index % len(spawns)]
        cx, cy = self.maze.tile_center(self.tile_r, self.tile_c)
        self.x = float(cx)
        self.y = float(cy)

        self.dir_x = 0
        self.dir_y = -1   # start moving up
        self.speed = ENEMY_BASE_SPEED
        # The red chaser must always pressure the player. Other personalities
        # keep their scatter/chase rhythm.
        self.mode = self.MODE_CHASE if self.personality == 0 else self.MODE_SCATTER
        self.mode_timer  = 0
        self.scared_timer = 0
        self.respawn_timer = 0
        self.pending_scared_frames = 0
        self.anim_tick   = 0
        self.blink        = False
        self.path_timer   = 0      # recalculate path every N frames
        self._next_tile   = None
        self.telegraph_target = None
        self.collision_disabled_frames = 0
        self._last_learning_state = None
        self._last_learning_action = None
        self._last_learning_target = None
        self._last_target_distance = None
        self._last_learning_distances = None
        self.recent_decisions = deque(maxlen=12)
        self.visited_tiles = {(self.tile_r, self.tile_c)}
        self.ability.reset()

    # ── Mode switching ────────────────────────────────────────────────────────

    def frighten(self, duration=POWER_DURATION):
        if self.mode == self.MODE_RESPAWNING:
            self.pending_scared_frames = max(
                self.pending_scared_frames,
                max(0, duration - self.respawn_timer),
            )
            return
        self.mode = self.MODE_SCARED
        self.scared_timer = max(1, int(duration))
        self.blink = False
        # Reverse direction
        self.dir_x, self.dir_y = -self.dir_x, -self.dir_y
        # Do not attribute frightened escape movement to the chase policy.
        self._last_learning_state = None
        self._last_learning_action = None
        self._last_learning_target = None
        self._last_target_distance = None
        self._last_learning_distances = None

    def end_fright(self):
        self.mode = self.MODE_CHASE if self.personality == 0 else self.MODE_SCATTER
        self.mode_timer = 0

    def respawn_after_eaten(self, power_frames):
        """Temporarily show harmless eyes, then rejoin the same power session."""
        self.reset()
        self.mode = self.MODE_RESPAWNING
        self.respawn_timer = min(ENEMY_RESPAWN_FRAMES, max(1, int(power_frames)))
        self.pending_scared_frames = max(0, int(power_frames) - self.respawn_timer)

    def cancel_pending_power(self):
        self.pending_scared_frames = 0

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, player, level: int, speed_scale=1.0, exploration_scale=1.0):
        self.anim_tick += 1
        self.exploration_scale = exploration_scale
        if self.collision_disabled_frames > 0:
            self.collision_disabled_frames -= 1

        if self.mode == self.MODE_RESPAWNING:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                remaining = self.pending_scared_frames
                self.pending_scared_frames = 0
                if remaining > 0:
                    self.mode = self.MODE_SCATTER
                    self.frighten(remaining)
                else:
                    self.end_fright()
            return

        # Speed scaling with level
        level_bonus = (level - 1) * ENEMY_SPEED_STEP
        base = min(ENEMY_BASE_SPEED + level_bonus, ENEMY_MAX_SPEED)
        ability_scale = self.ability.update(
            vulnerable=self.mode in (self.MODE_SCARED, self.MODE_RESPAWNING)
        )

        if self.mode == self.MODE_SCARED:
            self.scared_timer -= 1
            self.speed = ENEMY_SCARED_SPEED * speed_scale
            if self.scared_timer <= 0:
                self.end_fright()
            elif self.scared_timer <= POWER_BLINK_START:
                self.blink = (self.anim_tick // 10) % 2 == 0
        elif self.personality == 0:
            self.speed = base * speed_scale * ability_scale
            self.blink = False
            self.mode = self.MODE_CHASE
        else:
            self.speed = base * speed_scale * ability_scale
            self.blink = False
            # Alternate scatter/chase
            self.mode_timer += 1
            if self.mode == self.MODE_SCATTER and self.mode_timer > ENEMY_SCATTER_TICKS:
                self.mode = self.MODE_CHASE
                self.mode_timer = 0
            elif self.mode == self.MODE_CHASE and self.mode_timer > ENEMY_CHASE_TICKS:
                self.mode = self.MODE_SCATTER
                self.mode_timer = 0

        # Pick a new route only at a tile centre. Replanning mid-corridor caused
        # drones to jitter and occasionally turn back into walls.
        if self._next_tile is None:
            self._next_tile = self._choose_next_tile(player)

        # Move toward next tile
        if self._next_tile:
            self._move_toward(self._next_tile)

    def _choose_next_tile(self, player):
        """Return the adjacent tile (r,c) this enemy wants to move into."""
        pr, pc = player.tile_r, player.tile_c

        if self.mode == self.MODE_SCARED:
            return self._scared_target(player)
        elif self.mode == self.MODE_SCATTER:
            target = self.SCATTER_TARGETS[self.personality % 4]
        else:  # CHASE
            target = self._chase_target(pr, pc, player)
        target = self._nearest_passable(target)
        self.telegraph_target = target

        legal_tiles = self._legal_neighbors(allow_reverse=False)
        if not legal_tiles:
            legal_tiles = self._legal_neighbors(allow_reverse=True)
        if not legal_tiles:
            return (self.tile_r, self.tile_c)

        distances = self._route_distances(target)
        reachable = [distances[tile] for tile in legal_tiles if tile in distances]
        if self.mode == self.MODE_CHASE and reachable:
            # Learning may choose between equally short routes, but it may not
            # farm rewards by walking away from the target or oscillating.
            best_distance = min(reachable)
            decision_tiles = [tile for tile in legal_tiles
                              if distances.get(tile) == best_distance]
        else:
            decision_tiles = legal_tiles

        legal_actions = [action_for_step((self.tile_r, self.tile_c), tile)
                         for tile in decision_tiles]
        legal_actions = [action for action in legal_actions if action is not None]
        state = self.brain.encode_state(
            self.maze,
            (self.tile_r, self.tile_c),
            target,
            (self.dir_x, self.dir_y),
            self.mode,
        )

        if self._last_learning_state is not None:
            reward = self._movement_reward()
            self.brain.update(
                self._last_learning_state,
                self._last_learning_action,
                reward,
                state,
                legal_actions,
            )

        heuristic_tile = self._best_neighbor(target, distances)
        heuristic_action = action_for_step((self.tile_r, self.tile_c), heuristic_tile)
        epsilon = max(0.0, min(1.0, AI_EXPLORATION * self.exploration_scale))
        action = self.brain.choose_action(
            state, legal_actions, heuristic_action, epsilon=epsilon
        )
        if action is None:
            return heuristic_tile

        self._last_learning_state = state
        self._last_learning_action = action
        self._last_learning_target = target
        self._last_target_distance = distances.get(
            (self.tile_r, self.tile_c),
            self._distance((self.tile_r, self.tile_c), target),
        )
        self._last_learning_distances = distances
        self.recent_decisions.append((self.tile_r, self.tile_c))
        self.visited_tiles.add((self.tile_r, self.tile_c))
        dr, dc = ACTION_DELTAS[action]
        return (self.tile_r + dr, self.tile_c + dc)

    def _chase_target(self, pr, pc, player):
        if self.personality == 0:
            return (pr, pc)
        elif self.personality == 1:
            # 4 tiles ahead of player direction
            return (pr + player.dir_y * 4, pc + player.dir_x * 4)
        elif self.personality == 2:
            # Aim at the player's side to learn flanking instead of following.
            if player.dir_x or player.dir_y:
                side_r = -player.dir_x
                side_c = player.dir_y
                return (pr + side_r * 4, pc + side_c * 4)
            return (pr, pc)
        else:
            # Explorer learns from novelty rewards while remaining relevant to
            # the player's area rather than wandering into a remote corner.
            return (pr, pc)

    @staticmethod
    def _distance(position, target):
        return abs(position[0] - target[0]) + abs(position[1] - target[1])

    def _movement_reward(self):
        """Personality-specific reward shaping for the last chosen step."""
        current = (self.tile_r, self.tile_c)
        if self._last_learning_distances is not None:
            distance = self._last_learning_distances.get(
                current,
                self._distance(current, self._last_learning_target),
            )
        else:
            distance = self._distance(current, self._last_learning_target)
        improvement = self._last_target_distance - distance
        is_new = current not in self.visited_tiles
        repeated = current in self.recent_decisions
        repeat_penalty = 0.35 if repeated else 0.0

        if self.personality == 0:       # chaser: close distance aggressively
            return improvement * 2.0 + (0.08 if improvement > 0 else -0.60) - repeat_penalty
        if self.personality == 1:       # ambusher: reach predicted intercept
            return improvement * 1.6 + (0.06 if improvement > 0 else -0.35) - repeat_penalty
        if self.personality == 2:       # flanker: occupy the side target
            return improvement * 1.45 + (0.06 if improvement > 0 else -0.35) - repeat_penalty
        # explorer: discover new corridors and avoid repetitive loops
        return ((0.85 if is_new else -0.22)
                + improvement * 0.15 - repeat_penalty)

    def give_reward(self, reward):
        """Reward or punish the latest decision after a gameplay event."""
        self.brain.apply_event_reward(
            self._last_learning_state,
            self._last_learning_action,
            reward,
        )

    def _scared_target(self, player):
        """Choose the legal neighbour farthest from the player."""
        choices = self._legal_neighbors(allow_reverse=True)
        if not choices:
            return (self.tile_r, self.tile_c)
        random.shuffle(choices)
        return max(
            choices,
            key=lambda pos: (pos[0] - player.tile_r) ** 2
                            + (pos[1] - player.tile_c) ** 2,
        )

    def _route_distances(self, target_r_c):
        """Return true maze-route distances from every tile to the target."""
        target = self._nearest_passable(target_r_c)
        return self.maze.route_distances(target)

    def _best_neighbor(self, target_r_c, distances=None):
        """Return the first step of a shortest BFS route to the target."""
        target = self._nearest_passable(target_r_c)
        start = (self.tile_r, self.tile_c)
        legal_first = self._legal_neighbors(allow_reverse=False)
        if not legal_first:
            legal_first = self._legal_neighbors(allow_reverse=True)
        if not legal_first:
            return start
        distances = distances or self._route_distances(target)
        tr, tc = target
        return min(
            legal_first,
            key=lambda p: (distances.get(p, 10_000),
                           (p[0] - tr) ** 2 + (p[1] - tc) ** 2),
        )

    def _legal_neighbors(self, allow_reverse=False):
        reverse = (-self.dir_y, -self.dir_x)
        choices = []
        for dr, dc in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            if not allow_reverse and (dr, dc) == reverse:
                continue
            tile = (self.tile_r + dr, self.tile_c + dc)
            if not self.maze.is_wall_at(*tile):
                choices.append(tile)
        return choices

    def _nearest_passable(self, target):
        """Clamp an off-grid/wall personality target to a reachable tile."""
        tr = max(0, min(ROWS - 1, target[0]))
        tc = max(0, min(COLS - 1, target[1]))
        if not self.maze.is_wall_at(tr, tc):
            return (tr, tc)
        queue = deque([(tr, tc)])
        visited = {(tr, tc)}
        while queue:
            cr, cc = queue.popleft()
            for dr, dc in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < ROWS and 0 <= nc < COLS):
                    continue
                if (nr, nc) in visited:
                    continue
                if not self.maze.is_wall_at(nr, nc):
                    return (nr, nc)
                visited.add((nr, nc))
                queue.append((nr, nc))
        return (self.tile_r, self.tile_c)

    def _move_toward(self, target):
        if target is None:
            return
        tr, tc = target
        tx, ty = self.maze.tile_center(tr, tc)
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)
        if dist < self.speed + 1:
            # Arrive
            old_r, old_c = self.tile_r, self.tile_c
            self.x, self.y = float(tx), float(ty)
            self.tile_r, self.tile_c = tr, tc
            self.dir_x = tc - old_c
            self.dir_y = tr - old_r
            self._next_tile = None
        else:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed
            # Update tile and direction
            new_r, new_c = self.maze.pixel_to_tile(self.x, self.y)
            self.dir_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
            self.dir_y = 1 if dy > 0 else (-1 if dy < 0 else 0)
            self.tile_r, self.tile_c = new_r, new_c

    # ── Collision rect ────────────────────────────────────────────────────────

    @property
    def rect(self):
        r = TILE_SIZE // 2 - 4
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    def collides_with_player(self, player):
        return (self.mode != self.MODE_RESPAWNING
                and self.collision_disabled_frames == 0
                and self.rect.colliderect(player.rect))

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surf, offset_y):
        cx = int(self.x)
        cy = int(self.y) + offset_y
        t  = self.anim_tick

        if self.mode == self.MODE_RESPAWNING:
            # Eyes-only state makes the temporary non-collidable period clear.
            hover_y = cy + int(2 * math.sin(t * 0.16 + self.index))
            pygame.draw.circle(surf, (70, 100, 150), (cx, hover_y), 11, 1)
            for ox in (-4, 4):
                pygame.draw.circle(surf, (235, 250, 255), (cx + ox, hover_y), 3)
                pygame.draw.circle(surf, self.color, (cx + ox, hover_y), 1)
            return

        if self.mode == self.MODE_SCARED:
            body_color = ENEMY_BLINK if self.blink else ENEMY_SCARED
        else:
            body_color = self.color
            if self.ability.visibility < 1.0:
                body_color = tuple(max(24, int(channel * self.ability.visibility))
                                   for channel in body_color)

        # Outer glow
        gr = TILE_SIZE // 2 + 2
        glow = self._glow_cache.get(body_color)
        if glow is None:
            glow = pygame.Surface((gr * 4, gr * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*body_color, 40), (gr * 2, gr * 2), gr * 2)
            pygame.draw.circle(glow, (*body_color, 70), (gr * 2, gr * 2), gr)
            self._glow_cache[body_color] = glow
        surf.blit(glow, (cx - gr * 2, cy - gr * 2))

        # Drone body — rounded rect (hologram hex)
        body_r = TILE_SIZE // 2 - 3
        # Hover bob
        hover_y = cy + int(2 * math.sin(t * 0.12 + self.index))
        pygame.draw.circle(surf, body_color, (cx, hover_y), body_r)

        if self.ability.telegraph and self.mode not in (
                self.MODE_SCARED, self.MODE_RESPAWNING):
            warning = (255, 230, 80) if (t // 6) % 2 == 0 else self.color
            pygame.draw.circle(surf, warning, (cx, hover_y), body_r + 5, 2)
        elif self.ability.active and self.mode not in (
                self.MODE_SCARED, self.MODE_RESPAWNING):
            pygame.draw.circle(surf, self.color, (cx, hover_y), body_r + 3, 1)

        if (self.personality == 1 and self.telegraph_target
                and (self.ability.telegraph or self.ability.active)
                and self.mode not in (self.MODE_SCARED, self.MODE_RESPAWNING)):
            target_r, target_c = self.telegraph_target
            tx, ty = self.maze.tile_center(target_r, target_c)
            ty += offset_y
            marker = (255, 190, 70)
            pygame.draw.circle(surf, marker, (tx, ty), 7, 1)
            pygame.draw.line(surf, marker, (tx - 10, ty), (tx + 10, ty), 1)
            pygame.draw.line(surf, marker, (tx, ty - 10), (tx, ty + 10), 1)

        # Eyes (or glowing sensor)
        if self.mode != self.MODE_SCARED:
            eye_color = (255, 255, 255)
            pupil_color = (20, 20, 20)
            # Left eye
            pygame.draw.circle(surf, eye_color, (cx - 4, hover_y - 2), 3)
            pygame.draw.circle(surf, pupil_color, (cx - 4, hover_y - 2), 2)
            # Right eye
            pygame.draw.circle(surf, eye_color, (cx + 4, hover_y - 2), 3)
            pygame.draw.circle(surf, pupil_color, (cx + 4, hover_y - 2), 2)
        else:
            # X eyes when scared
            for ox in (-4, 4):
                ex, ey = cx + ox, hover_y - 2
                pygame.draw.line(surf, (200, 200, 255), (ex - 2, ey - 2), (ex + 2, ey + 2), 1)
                pygame.draw.line(surf, (200, 200, 255), (ex + 2, ey - 2), (ex - 2, ey + 2), 1)

        # Scan ring (rotating)
        angle = t * 0.08 * (1 if self.index % 2 == 0 else -1)
        ring_cx = cx
        ring_cy = hover_y
        ring_color = tuple(max(18, int(channel * 0.35)) for channel in body_color)
        pygame.draw.circle(surf, ring_color, (ring_cx, ring_cy), body_r * 2, 1)
        # Dot on ring
        dot_x = ring_cx + int((body_r * 2 - 2) * math.cos(angle))
        dot_y = ring_cy + int((body_r * 2 - 2) * math.sin(angle))
        pygame.draw.circle(surf, body_color, (dot_x, dot_y), 2)
