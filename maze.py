# maze.py — Maze parsing, rendering, and collision helpers

import pygame
import math
import random
from collections import OrderedDict, deque
from settings import *
from powerups import POWERUP_BY_KEY, assign_powerups
from localization import current_language


class Maze:
    """
    Parses MAZE_LAYOUT string grid into a 2-D tile array.
    Handles drawing (walls + dots + power pellets + portals).
    Provides collision / query helpers used by player and enemies.
    """

    # Tile type constants
    WALL  = 1
    DOT   = 0
    POWER = 7
    PORTAL= 8
    EMPTY = 9

    def __init__(self, seed=None, procedural=True):
        self.seed = seed if seed is not None else random.SystemRandom().randrange(1, 2**31)
        self.player_spawn = (ROWS - 2, 13)
        self.enemy_spawns = [
            (PORTAL_ROW, 13),
            (PORTAL_ROW, 11),
            (PORTAL_ROW, 15),
            (PORTAL_ROW - 2, 13),
        ]
        self.portals = dict(PORTALS)
        layout = self._generate_layout() if procedural else MAZE_LAYOUT
        self._parse_layout(layout)
        self._build_navigation_cache()
        power_positions = [
            (r, c)
            for r, row in enumerate(self.tiles)
            for c, tile in enumerate(row)
            if tile == self.POWER
        ]
        self.power_kinds = assign_powerups(self.seed, power_positions)
        if not pygame.font.get_init():
            pygame.font.init()
        self._power_label_font = pygame.font.SysFont("DejaVu Sans", 10, bold=True)
        self._power_label_cache = {}
        self.show_power_labels = True
        self._build_wall_surface()
        self._build_item_sprites()
        self.anim_tick = 0        # used for pulsing animations
        self.total_dots = sum(
            1 for row in self.tiles if row for t in row
            if t in (self.DOT, self.POWER)
        )
        self.dots_remaining = self.total_dots

    def _build_navigation_cache(self):
        """Precompute static neighbours and keep a small route-map LRU.

        Sentinel pathfinding used to scan the complete maze for every turn.
        The maze walls never change, so neighbour discovery is done once and
        recently requested destination maps are shared by all Sentinels.
        """
        self._nav_neighbors = {}
        for r in range(ROWS):
            for c in range(COLS):
                if self.is_wall_at(r, c):
                    continue
                self._nav_neighbors[(r, c)] = tuple(
                    (r + dr, c + dc)
                    for dr, dc in ((0, -1), (0, 1), (-1, 0), (1, 0))
                    if not self.is_wall_at(r + dr, c + dc)
                )
        self._route_cache = OrderedDict()
        self._route_cache_limit = 24

    def route_distances(self, target):
        """Return a shared BFS distance map for a passable destination."""
        cached = self._route_cache.get(target)
        if cached is not None:
            self._route_cache.move_to_end(target)
            return cached

        distances = {target: 0}
        queue = deque([target])
        while queue:
            current = queue.popleft()
            next_distance = distances[current] + 1
            for neighbour in self._nav_neighbors.get(current, ()):
                if neighbour in distances:
                    continue
                distances[neighbour] = next_distance
                queue.append(neighbour)

        self._route_cache[target] = distances
        self._route_cache.move_to_end(target)
        while len(self._route_cache) > self._route_cache_limit:
            self._route_cache.popitem(last=False)
        return distances

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _generate_layout(self):
        """Build a connected maze with DFS, extra loops and a central hub.

        The same seed always creates the same level. All corridor nodes belong
        to one connected component, which means every generated collectible is
        reachable and every level can be completed.
        """
        rng = random.Random(self.seed)
        grid = [['1' for _ in range(COLS)] for _ in range(ROWS)]
        node_rows = list(range(1, ROWS - 1, 2))
        node_cols = list(range(1, COLS - 2, 2))

        start = self.player_spawn
        stack = [start]
        visited = {start}
        grid[start[0]][start[1]] = '0'

        while stack:
            r, c = stack[-1]
            candidates = []
            for dr, dc in ((0, -2), (0, 2), (-2, 0), (2, 0)):
                nr, nc = r + dr, c + dc
                if nr in node_rows and nc in node_cols and (nr, nc) not in visited:
                    candidates.append((nr, nc, dr, dc))
            if not candidates:
                stack.pop()
                continue
            nr, nc, dr, dc = rng.choice(candidates)
            grid[r + dr // 2][c + dc // 2] = '0'
            grid[nr][nc] = '0'
            visited.add((nr, nc))
            stack.append((nr, nc))

        # Open selected separating walls to create alternate routes and prevent
        # the generated mazes from feeling like long single-path tunnels.
        loop_candidates = []
        for r in range(1, ROWS - 1):
            for c in range(1, COLS - 1):
                if grid[r][c] != '1':
                    continue
                horizontal = grid[r][c - 1] == '0' and grid[r][c + 1] == '0'
                vertical = grid[r - 1][c] == '0' and grid[r + 1][c] == '0'
                if horizontal != vertical:
                    loop_candidates.append((r, c))
        rng.shuffle(loop_candidates)
        for r, c in loop_candidates[:max(24, len(visited) // 4)]:
            grid[r][c] = '0'

        # Central sentinel hub. It is connected to the carved network because
        # its odd-coordinate cells were already part of the DFS graph.
        for r in range(PORTAL_ROW - 2, PORTAL_ROW + 3):
            for c in range(11, 16):
                grid[r][c] = ' '

        # Left/right tunnel portals and their approach tiles.
        grid[PORTAL_ROW][0] = '8'
        grid[PORTAL_ROW][1] = '0'
        grid[PORTAL_ROW][COLS - 2] = '0'
        grid[PORTAL_ROW][COLS - 1] = '8'

        # Six ability cores are kept on DFS corridor nodes so every power-up
        # appears exactly once and is always reachable.
        for r, c in (
            (3, 1), (3, 25), (9, 5),
            (ROWS - 10, 21), (ROWS - 4, 1), (ROWS - 4, 25),
        ):
            grid[r][c] = '7'

        # Spawn cells never contain a collectible.
        pr, pc = self.player_spawn
        grid[pr][pc] = ' '
        for r, c in self.enemy_spawns:
            grid[r][c] = ' '

        return [''.join(row) for row in grid]

    def _parse_layout(self, layout):
        self.tiles = []
        for raw_row in layout:
            # Pad / trim to exactly COLS characters
            row_str = raw_row.ljust(COLS)[:COLS]
            row = []
            for ch in row_str:
                if ch == '1':
                    row.append(self.WALL)
                elif ch == '7':
                    row.append(self.POWER)
                elif ch == '8':
                    row.append(self.PORTAL)
                elif ch == '9' or ch == ' ':
                    row.append(self.EMPTY)
                else:          # '0' or any digit
                    row.append(self.DOT)
            self.tiles.append(row)

    # ── Static wall surface (drawn once, blitted each frame) ──────────────────

    def _build_wall_surface(self):
        self._wall_surf = pygame.Surface((SCREEN_W, ROWS * TILE_SIZE), pygame.SRCALPHA)
        self._wall_surf.fill((0, 0, 0, 0))
        for r, row in enumerate(self.tiles):
            for c, tile in enumerate(row):
                if tile == self.WALL:
                    self._draw_wall_tile(self._wall_surf, r, c)

    def _build_item_sprites(self):
        """Pre-render animated items once instead of allocating per dot/frame."""
        self._dot_sprites = []
        radius = 3
        for frame in range(12):
            glow_alpha = int(140 + 60 * math.sin(frame * math.tau / 12))
            sprite = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
            pygame.draw.circle(sprite, (*DOT_COLOR, glow_alpha // 2),
                               (radius * 3, radius * 3), radius + 2)
            pygame.draw.circle(sprite, (*DOT_COLOR, 220),
                               (radius * 3, radius * 3), radius)
            self._dot_sprites.append(sprite)

        self._power_sprites = {key: [] for key in POWERUP_BY_KEY}
        self._portal_sprites = []
        sprite_size = 56
        center = sprite_size // 2
        for frame in range(16):
            wave = math.sin(frame * math.tau / 16)
            pulse = int(8 + 4 * wave)
            alpha = int(180 + 75 * wave)
            for key, definition in POWERUP_BY_KEY.items():
                power = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
                pygame.draw.circle(power, (*definition.color, alpha // 3),
                                   (center, center), pulse * 2)
                pygame.draw.circle(power, (*definition.color, alpha),
                                   (center, center), pulse)
                self._power_sprites[key].append(power)

            radius_portal = int(TILE_SIZE // 2 - 2 + 3 * wave)
            portal = pygame.Surface((sprite_size, sprite_size), pygame.SRCALPHA)
            pygame.draw.circle(portal, (*PORTAL_COLOR, alpha // 2),
                               (center, center), radius_portal * 2)
            pygame.draw.circle(portal, (*PORTAL_COLOR, alpha),
                               (center, center), radius_portal)
            self._portal_sprites.append(portal)

    def _draw_wall_tile(self, surf, r, c):
        x = c * TILE_SIZE
        y = r * TILE_SIZE
        rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
        # Dark inner fill
        pygame.draw.rect(surf, WALL_INNER, rect)
        # Neon border — only draw edges that face a non-wall tile
        lw = 2
        if not self._is_wall(r - 1, c):
            pygame.draw.line(surf, WALL_COLOR, (x, y), (x + TILE_SIZE, y), lw)
        if not self._is_wall(r + 1, c):
            pygame.draw.line(surf, WALL_COLOR, (x, y + TILE_SIZE - 1), (x + TILE_SIZE, y + TILE_SIZE - 1), lw)
        if not self._is_wall(r, c - 1):
            pygame.draw.line(surf, WALL_COLOR, (x, y), (x, y + TILE_SIZE), lw)
        if not self._is_wall(r, c + 1):
            pygame.draw.line(surf, WALL_COLOR, (x + TILE_SIZE - 1, y), (x + TILE_SIZE - 1, y + TILE_SIZE), lw)

    def _is_wall(self, r, c):
        if r < 0 or r >= ROWS or c < 0 or c >= COLS:
            return False          # treat out-of-bounds as passable (portals)
        return self.tiles[r][c] == self.WALL

    # ── Per-frame draw ────────────────────────────────────────────────────────

    def draw(self, surf, offset_y=0):
        self.anim_tick += 1
        # Draw static walls
        surf.blit(self._wall_surf, (0, offset_y))
        # Draw dots + power pellets (dynamic so they can be removed)
        self._draw_items(surf, offset_y)
        # Portal glow
        self._draw_portals(surf, offset_y)

    def _draw_items(self, surf, oy):
        t = self.anim_tick
        power_labels = []
        for r, row in enumerate(self.tiles):
            for c, tile in enumerate(row):
                cx = c * TILE_SIZE + TILE_SIZE // 2
                cy = r * TILE_SIZE + TILE_SIZE // 2 + oy

                if tile == self.DOT:
                    sprite = self._dot_sprites[(t // 3 + c + r) % len(self._dot_sprites)]
                    surf.blit(sprite, (cx - sprite.get_width() // 2,
                                       cy - sprite.get_height() // 2))

                elif tile == self.POWER:
                    key = self.power_kinds.get((r, c), "overclock")
                    sprites = self._power_sprites[key]
                    sprite = sprites[(t // 3) % len(sprites)]
                    surf.blit(sprite, (cx - sprite.get_width() // 2,
                                       cy - sprite.get_height() // 2))
                    if self.show_power_labels:
                        power_labels.append((cx, cy, key))

        # Labels are drawn last so nearby dots and glow sprites cannot cover
        # the text.  Each has its own dark plate for maze-wall contrast.
        for cx, cy, key in power_labels:
            self._draw_power_label(surf, cx, cy, key)

    def _draw_power_label(self, surf, cx, cy, key):
        language = current_language()
        cache_key = (language, key)
        label_surface = self._power_label_cache.get(cache_key)
        if label_surface is None:
            definition = POWERUP_BY_KEY[key]
            name = definition.label_tr if language == "tr" else definition.label_en
            text = self._power_label_font.render(name.upper(), True, (245, 250, 255))
            label_surface = pygame.Surface(
                (text.get_width() + 10, text.get_height() + 6), pygame.SRCALPHA
            )
            label_surface.fill((2, 8, 20, 225))
            pygame.draw.rect(label_surface, (*definition.color, 245),
                             label_surface.get_rect(), 1, border_radius=4)
            label_surface.blit(text, (5, 3))
            self._power_label_cache[cache_key] = label_surface

        x = max(2, min(SCREEN_W - label_surface.get_width() - 2,
                       cx - label_surface.get_width() // 2))
        y = max(2, cy - 30)
        surf.blit(label_surface, (x, y))

    def _draw_portals(self, surf, oy):
        t = self.anim_tick
        for (r, c) in self.portals:
            cx = c * TILE_SIZE + TILE_SIZE // 2
            cy = r * TILE_SIZE + TILE_SIZE // 2 + oy
            sprite = self._portal_sprites[(t // 3) % len(self._portal_sprites)]
            surf.blit(sprite, (cx - sprite.get_width() // 2,
                               cy - sprite.get_height() // 2))

    # ── Tile queries ──────────────────────────────────────────────────────────

    def tile_at(self, r, c):
        if 0 <= r < ROWS and 0 <= c < COLS:
            return self.tiles[r][c]
        # Gameplay queries treat the edge as solid. Portals themselves live
        # inside the grid, so actors cannot accidentally leave the playfield.
        return self.WALL

    def is_wall_at(self, r, c):
        return self.tile_at(r, c) == self.WALL

    def pixel_to_tile(self, px, py):
        return int(py // TILE_SIZE), int(px // TILE_SIZE)

    def tile_center(self, r, c):
        return (c * TILE_SIZE + TILE_SIZE // 2,
                r * TILE_SIZE + TILE_SIZE // 2)

    def collect(self, r, c):
        """Remove dot/power at (r,c). Returns score earned or 0."""
        tile = self.tile_at(r, c)
        if tile == self.DOT:
            self.tiles[r][c] = self.EMPTY
            self.dots_remaining -= 1
            return DOT_SCORE
        if tile == self.POWER:
            self.tiles[r][c] = self.EMPTY
            self.dots_remaining -= 1
            return POWER_SCORE
        return 0

    def is_power(self, r, c):
        return self.tile_at(r, c) == self.POWER

    def power_kind(self, r, c):
        if not self.is_power(r, c):
            return None
        return self.power_kinds.get((r, c), "overclock")

    def collect_dots_near(self, r, c, radius=3):
        """Collect ordinary dots in a Manhattan radius for the magnet power."""
        collected = []
        for nr in range(max(0, r - radius), min(ROWS, r + radius + 1)):
            for nc in range(max(0, c - radius), min(COLS, c + radius + 1)):
                if abs(nr - r) + abs(nc - c) > radius:
                    continue
                if self.tiles[nr][nc] == self.DOT:
                    self.tiles[nr][nc] = self.EMPTY
                    self.dots_remaining -= 1
                    collected.append((nr, nc))
        return collected

    def portal_exit(self, r, c):
        """Return exit tile (r2,c2) if (r,c) is a portal, else None."""
        return self.portals.get((r, c))

    def all_dots_collected(self):
        return self.dots_remaining == 0
