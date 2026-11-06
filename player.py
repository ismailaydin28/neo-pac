# player.py — NeoPac Player (Digital Avatar)

import pygame
import math
from settings import *


_TRAIL_SPRITES = {}
_PLAYER_GLOWS = {}
_DASH_RINGS = {}


class TrailParticle:
    """Single particle in the player's movement trail."""

    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.life = 20          # frames until gone
        self.max_life = 20

    def update(self):
        self.life -= 1

    def draw(self, surf, offset_y):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        radius = max(1, int(5 * (self.life / self.max_life)))
        alpha_bucket = min(255, (alpha // 32) * 32)
        key = (self.color, radius, alpha_bucket)
        glow = _TRAIL_SPRITES.get(key)
        if glow is None:
            glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            col = (*self.color, alpha_bucket)
            pygame.draw.circle(glow, col, (radius * 2, radius * 2), radius)
            _TRAIL_SPRITES[key] = glow
        surf.blit(glow, (self.x - radius * 2, self.y - radius * 2 + offset_y))


class Player:
    """
    Grid-aligned player movement with sub-pixel smoothing.
    Features: dash, trail, neon glow draw, portal teleport.
    """

    def __init__(self, maze):
        self.maze = maze
        self.reset()

    def reset(self, invincible=False):
        # Spawn is supplied by the current generated maze.
        self.tile_r, self.tile_c = self.maze.player_spawn
        cx, cy = self.maze.tile_center(self.tile_r, self.tile_c)
        self.x = float(cx)
        self.y = float(cy)

        self.dir_x = 0
        self.dir_y = 0
        self.next_dir_x = 0
        self.next_dir_y = 0

        self.speed = PLAYER_SPEED
        self.alive = True
        self.anim_tick = 0

        # Dash
        self.dash_frames_left = 0
        self.dash_cooldown    = 0

        # Trail
        self.trail: list[TrailParticle] = []
        self.trail_timer = 0

        # Invincibility after respawn
        self.invincible_frames = RESPAWN_INVINCIBLE_FRAMES if invincible else 0

        # Prevent a portal from bouncing the player between both exits.
        self.portal_cooldown = 0

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_input(self, keys):
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.next_dir_x, self.next_dir_y = -1,  0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.next_dir_x, self.next_dir_y =  1,  0
        if keys[pygame.K_UP]    or keys[pygame.K_w]: self.next_dir_x, self.next_dir_y =  0, -1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: self.next_dir_x, self.next_dir_y =  0,  1

    def set_direction(self, dx, dy):
        if dx or dy:
            self.next_dir_x, self.next_dir_y = dx, dy

    def request_dash(self):
        """Start a dash once per key press, if it is currently available."""
        if self.dash_cooldown == 0 and (self.dir_x or self.dir_y):
            self.dash_frames_left = PLAYER_DASH_FRAMES
            self.dash_cooldown    = PLAYER_DASH_COOLDOWN
            return True
        return False

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self):
        self.anim_tick += 1
        if self.invincible_frames > 0:
            self.invincible_frames -= 1
        if self.portal_cooldown > 0:
            self.portal_cooldown -= 1

        # Dash countdown
        was_dashing = self.dash_frames_left > 0
        if was_dashing:
            self.dash_frames_left -= 1
            current_speed = PLAYER_DASH_SPEED
        else:
            current_speed = PLAYER_SPEED
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        # Try to turn into requested direction
        if self._can_move(self.next_dir_x, self.next_dir_y, PLAYER_SPEED):
            self.dir_x, self.dir_y = self.next_dir_x, self.next_dir_y

        # Move if direction is valid
        if self._can_move(self.dir_x, self.dir_y, current_speed):
            self.x += self.dir_x * current_speed
            self.y += self.dir_y * current_speed
            self._snap_to_grid()
        else:
            # A dash can stop between grid centres because its 7 px step does
            # not divide the 24 px tile size. Centre the player on impact so a
            # buffered perpendicular turn is never rejected by a side wall.
            self._center_snap()
            if was_dashing:
                self.dash_frames_left = 0

        # Portal teleport
        self._check_portal()

        # Trail particles
        self._update_trail()

    def _can_move(self, dx, dy, step):
        if dx == 0 and dy == 0:
            return False
        # Predict next center position
        nx = self.x + dx * step
        ny = self.y + dy * step
        # Check the two corners in the direction of motion
        # Match the actual collision rectangle. The old 11 px margin was wider
        # than the visible 8 px body and falsely blocked turns near walls.
        margin = TILE_SIZE // 2 - 4
        if dx != 0:
            corners_y = [ny - margin, ny + margin]
            check_x = nx + dx * margin
            for cy in corners_y:
                r, c = self.maze.pixel_to_tile(check_x, cy)
                if self.maze.is_wall_at(r, c):
                    return False
        if dy != 0:
            corners_x = [nx - margin, nx + margin]
            check_y = ny + dy * margin
            for cx in corners_x:
                r, c = self.maze.pixel_to_tile(cx, check_y)
                if self.maze.is_wall_at(r, c):
                    return False
        return True

    def _snap_to_grid(self):
        """Keep movement axis-aligned so turns feel precise."""
        if self.dir_x != 0:   # horizontal — snap Y to row center
            target_y = self.tile_r * TILE_SIZE + TILE_SIZE // 2
            self.y += (target_y - self.y) * 0.3
        if self.dir_y != 0:   # vertical — snap X to column center
            target_x = self.tile_c * TILE_SIZE + TILE_SIZE // 2
            self.x += (target_x - self.x) * 0.3
        # Update tile coords
        self.tile_r, self.tile_c = self.maze.pixel_to_tile(self.x, self.y)

    def _center_snap(self):
        self.tile_r, self.tile_c = self.maze.pixel_to_tile(self.x, self.y)
        cx, cy = self.maze.tile_center(self.tile_r, self.tile_c)
        self.x, self.y = float(cx), float(cy)

    def _check_portal(self):
        if self.portal_cooldown > 0:
            return
        exit_tile = self.maze.portal_exit(self.tile_r, self.tile_c)
        if exit_tile:
            er, ec = exit_tile
            self.tile_r, self.tile_c = er, ec
            cx, cy = self.maze.tile_center(er, ec)
            self.x, self.y = float(cx), float(cy)
            self.portal_cooldown = 12

    def _update_trail(self):
        self.trail_timer += 1
        if self.trail_timer >= 3 and (self.dir_x or self.dir_y):
            self.trail_timer = 0
            color = PLAYER_TRAIL if self.dash_frames_left == 0 else (100, 220, 255)
            self.trail.append(TrailParticle(self.x, self.y, color))
        for p in self.trail:
            p.update()
        self.trail = [p for p in self.trail if p.life > 0]

    # ── Collectibles ──────────────────────────────────────────────────────────

    def collect(self):
        """Call each frame; returns (score_earned, power-up key or None)."""
        power_kind = self.maze.power_kind(self.tile_r, self.tile_c)
        score = self.maze.collect(self.tile_r, self.tile_c)
        return score, power_kind

    # ── Collision rect ────────────────────────────────────────────────────────

    @property
    def rect(self):
        r = TILE_SIZE // 2 - 4
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surf, offset_y):
        # Draw trail first (behind player)
        for p in self.trail:
            p.draw(surf, offset_y)

        # Blink when invincible
        if self.invincible_frames > 0 and (self.anim_tick // 6) % 2 == 0:
            return

        t = self.anim_tick
        cx = int(self.x)
        cy = int(self.y) + offset_y

        # Outer glow
        glow_r = int(TILE_SIZE // 2 + 4 * math.sin(t * 0.15))
        glow_surf = _PLAYER_GLOWS.get(glow_r)
        if glow_surf is None:
            glow_surf = pygame.Surface((glow_r * 4, glow_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*PLAYER_COLOR, 50),
                               (glow_r * 2, glow_r * 2), glow_r * 2)
            pygame.draw.circle(glow_surf, (*PLAYER_COLOR, 90),
                               (glow_r * 2, glow_r * 2), glow_r)
            _PLAYER_GLOWS[glow_r] = glow_surf
        surf.blit(glow_surf, (cx - glow_r * 2, cy - glow_r * 2))

        # Core sphere — hexagonal approximation
        core_r = TILE_SIZE // 2 - 3
        pygame.draw.circle(surf, PLAYER_COLOR, (cx, cy), core_r)
        # Bright inner highlight
        pygame.draw.circle(surf, (200, 240, 255), (cx - 3, cy - 3), core_r // 3)

        # Dash afterimage rings
        if self.dash_frames_left > 0:
            ring_alpha = int(255 * self.dash_frames_left / PLAYER_DASH_FRAMES)
            alpha_bucket = min(255, (ring_alpha // 32) * 32)
            ring_surf = _DASH_RINGS.get(alpha_bucket)
            if ring_surf is None:
                ring_surf = pygame.Surface((core_r * 6, core_r * 6), pygame.SRCALPHA)
                pygame.draw.circle(ring_surf, (100, 220, 255, alpha_bucket),
                                   (core_r * 3, core_r * 3), core_r * 2, 2)
                _DASH_RINGS[alpha_bucket] = ring_surf
            surf.blit(ring_surf, (cx - core_r * 3, cy - core_r * 3))
