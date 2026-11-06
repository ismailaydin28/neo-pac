# ui.py — NeoPac HUD, Menus, Particle Effects, Screen Flash

import pygame
import math
import random
from settings import *
from localization import tr


_PARTICLE_SPRITES = {}


# ── Utility ───────────────────────────────────────────────────────────────────

def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Try to load a system monospace font; fall back to default."""
    candidates = ["DejaVu Sans Mono", "Courier New", "Courier", "monospace"]
    for name in candidates:
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f:
                return f
        except Exception:
            pass
    return pygame.font.Font(None, size)


# ── Particle system (generic) ─────────────────────────────────────────────────

class Particle:
    def __init__(self, x, y, color, vel_x, vel_y, life, size=3):
        self.x, self.y   = float(x), float(y)
        self.vx, self.vy = vel_x, vel_y
        self.color       = color
        self.life        = life
        self.max_life    = life
        self.size        = size

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.08   # mild gravity
        self.life -= 1

    def draw(self, surf):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        r = max(1, int(self.size * (self.life / self.max_life)))
        alpha_bucket = min(255, (alpha // 32) * 32)
        cache_key = (self.color, r, alpha_bucket)
        gs = _PARTICLE_SPRITES.get(cache_key)
        if gs is None:
            gs = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*self.color, alpha_bucket), (r * 2, r * 2), r)
            _PARTICLE_SPRITES[cache_key] = gs
        surf.blit(gs, (self.x - r * 2, self.y - r * 2))


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []

    def burst(self, x, y, color, count=12, speed=3.0, life=30):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            sp    = random.uniform(0.5, speed)
            self.particles.append(
                Particle(x, y, color,
                         math.cos(angle) * sp,
                         math.sin(angle) * sp,
                         random.randint(life // 2, life),
                         size=random.randint(2, 5))
            )

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)


# ── Screen flash ──────────────────────────────────────────────────────────────

class ScreenFlash:
    def __init__(self):
        self.frames   = 0
        self.color    = (255, 255, 255)
        self.max_frames = 0
        self._surface = None
        self.strength = 1.0

    def trigger(self, color=(255, 255, 255), frames=15):
        self.color = color
        self.frames = frames
        self.max_frames = frames

    def update(self):
        if self.frames > 0:
            self.frames -= 1

    def draw(self, surf):
        if self.frames <= 0:
            return
        alpha = int(180 * self.strength * (self.frames / self.max_frames))
        if alpha <= 0:
            return
        if self._surface is None or self._surface.get_size() != surf.get_size():
            self._surface = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        self._surface.fill((*self.color, alpha))
        surf.blit(self._surface, (0, 0))


# ── Scanline overlay ──────────────────────────────────────────────────────────

class ScanlineOverlay:
    def __init__(self, screen_w, screen_h):
        self._surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        for y in range(0, screen_h, 4):
            pygame.draw.line(self._surf, (0, 0, 0, 40), (0, y), (screen_w, y))

    def draw(self, surf):
        surf.blit(self._surf, (0, 0))


# ── HUD ───────────────────────────────────────────────────────────────────────

class HUD:
    def __init__(self):
        self.font_lg = load_font(22, bold=True)
        self.font_sm = load_font(16)
        self.anim_tick = 0
        self.combo_text = ""
        self.combo_timer = 0

    def show_combo(self, text: str):
        self.combo_text  = text
        self.combo_timer = 90

    def update(self):
        self.anim_tick += 1
        if self.combo_timer > 0:
            self.combo_timer -= 1

    def draw(self, surf, score: int, lives: int, level: int, high_score: int,
             power_timer: int, dash_cooldown: int, muted: bool,
             power_duration: int = POWER_DURATION, status_text: str = "",
             time_seconds: int | None = None, shield_count: int = 0):
        """Draw the HUD strip at the bottom of the screen."""
        hud_y = ROWS * TILE_SIZE
        hud_rect = pygame.Rect(0, hud_y, SCREEN_W, 60)
        pygame.draw.rect(surf, HUD_BG, hud_rect)
        # Top separator line (neon)
        pygame.draw.line(surf, WALL_COLOR, (0, hud_y), (SCREEN_W, hud_y), 1)

        t = self.anim_tick

        # ── Score ──
        score_lbl = self.font_sm.render(tr("score"), True, HUD_TEXT)
        surf.blit(score_lbl, (10, hud_y + 4))
        score_val = self.font_lg.render(f"{score:07d}", True, SCORE_COLOR)
        surf.blit(score_val, (10, hud_y + 20))

        # ── Session high score ──
        hi_lbl = self.font_sm.render(tr("high_score"), True, HUD_TEXT)
        surf.blit(hi_lbl, (145, hud_y + 4))
        hi_val = self.font_lg.render(f"{high_score:07d}", True, (180, 230, 255))
        surf.blit(hi_val, (145, hud_y + 20))

        # ── Level ──
        lvl_lbl = self.font_sm.render(tr("level", level=level), True, HUD_TEXT)
        surf.blit(lvl_lbl, (SCREEN_W // 2 - 25, hud_y + 8))

        # ── Lives (small circles) ──
        for i in range(lives):
            lx = SCREEN_W - 20 - i * 22
            ly = hud_y + 30
            pygame.draw.circle(surf, LIFE_COLOR, (lx, ly), 8)
            pygame.draw.circle(surf, (200, 240, 255), (lx - 2, ly - 2), 3)
        lives_lbl = self.font_sm.render(tr("lives"), True, HUD_TEXT)
        surf.blit(lives_lbl, (SCREEN_W - 20 - lives * 22 - 50, hud_y + 22))

        sound_lbl = self.font_sm.render(tr("muted") if muted else tr("sound"), True,
                                        (255, 100, 120) if muted else HUD_TEXT)
        surf.blit(sound_lbl, (SCREEN_W - sound_lbl.get_width() - 8, hud_y + 3))

        # ── Power mode bar ──
        if power_timer > 0:
            bar_w = int(120 * min(1.0, power_timer / max(1, power_duration)))
            pulse = 0.72 + 0.28 * ((math.sin(t * 0.15) + 1.0) / 2.0)
            bar_color = tuple(int(channel * pulse) for channel in ENERGY_COLOR)
            pygame.draw.rect(surf, bar_color,
                             (SCREEN_W // 2 - 60, hud_y + 44, bar_w, 8))
            pygame.draw.rect(surf, ENERGY_COLOR,
                             (SCREEN_W // 2 - 60, hud_y + 44, 120, 8), 1)
            em_lbl = self.font_sm.render(tr("overclock"), True, ENERGY_COLOR)
            surf.blit(em_lbl, (SCREEN_W // 2 - 60, hud_y + 28))
        elif status_text:
            active_lbl = self.font_sm.render(status_text, True, ENERGY_COLOR)
            surf.blit(active_lbl, (SCREEN_W // 2 - active_lbl.get_width() // 2,
                                   hud_y + 28))

        if time_seconds is not None:
            timer = self.font_sm.render(tr("time_left", seconds=max(0, time_seconds)),
                                        True, SCORE_COLOR)
            surf.blit(timer, (SCREEN_W // 2 - timer.get_width() // 2, hud_y + 4))
        if shield_count:
            shield = self.font_sm.render(tr("shield", count=shield_count),
                                         True, (100, 220, 255))
            surf.blit(shield, (SCREEN_W // 2 - shield.get_width() // 2, hud_y + 45))

        # ── Dash cooldown arc ──
        if dash_cooldown > 0:
            progress = 1.0 - (dash_cooldown / PLAYER_DASH_COOLDOWN)
            arc_color = (100, 220, 255)
        else:
            progress = 1.0
            arc_color = (60, 180, 255)
        # Simple bar
        dash_bar_x = SCREEN_W // 2 + 70
        dash_bar_y = hud_y + 42
        pygame.draw.rect(surf, (30, 30, 60), (dash_bar_x, dash_bar_y, 60, 6))
        pygame.draw.rect(surf, arc_color, (dash_bar_x, dash_bar_y, int(60 * progress), 6))
        dash_lbl = self.font_sm.render(tr("dash"), True, HUD_TEXT)
        surf.blit(dash_lbl, (dash_bar_x, hud_y + 28))

        # ── Combo float text ──
        if self.combo_timer > 0:
            alpha = min(255, self.combo_timer * 5)
            combo_surf = self.font_lg.render(self.combo_text, True, SCORE_COLOR)
            combo_surf.set_alpha(alpha)
            surf.blit(combo_surf, (SCREEN_W // 2 - combo_surf.get_width() // 2,
                                   ROWS * TILE_SIZE - 60 - (90 - self.combo_timer) // 3))


# ── Menu screen ───────────────────────────────────────────────────────────────

class MenuScreen:
    def __init__(self):
        self.font_title = load_font(46, bold=True)
        self.font_sub = load_font(18)
        self.font_tab = load_font(14, bold=True)
        self.font_item = load_font(19, bold=True)
        self.font_value = load_font(16, bold=True)
        self.font_detail = load_font(13)
        self.anim_tick = 0
        self.tab_rects = []
        self.row_rects = []
        self._stars = [(random.randint(0, SCREEN_W),
                        random.randint(0, SCREEN_H),
                        random.uniform(0.5, 2.5)) for _ in range(70)]

    def update(self):
        self.anim_tick += 1

    def draw(self, surf, tabs, active_tab, selected_item, rows):
        """Draw a compact tabbed settings menu and remember mouse hit boxes."""
        surf.fill(DARK_BG)
        t = self.anim_tick

        # Drifting stars
        for i, (sx, sy, speed) in enumerate(self._stars):
            ny = (sy + speed) % SCREEN_H
            self._stars[i] = (sx, ny, speed)
            brightness = int(100 + 155 * ((t * speed * 0.01 + i) % 1.0))
            pygame.draw.circle(surf, (brightness, brightness, brightness), (int(sx), int(ny)), 1)

        # Grid lines (cyberpunk floor effect)
        for x in range(0, SCREEN_W, TILE_SIZE):
            alpha = 25 + int(15 * math.sin(t * 0.03 + x * 0.1))
            pygame.draw.line(surf, (0, alpha * 3, alpha * 4), (x, 0), (x, SCREEN_H))
        for y in range(0, SCREEN_H, TILE_SIZE):
            alpha = 20 + int(10 * math.sin(t * 0.02 + y * 0.08))
            pygame.draw.line(surf, (0, alpha * 2, alpha * 3), (0, y), (SCREEN_W, y))

        # Compact title leaves the majority of the screen to organized tabs.
        title_text = "NEOPAC"
        ty = 26
        glow_alpha = int(100 + 80 * math.sin(t * 0.05))
        for offset in range(2, 0, -1):
            ghost = self.font_title.render(title_text, True, WALL_COLOR)
            ghost.set_alpha(glow_alpha // offset)
            surf.blit(ghost, (SCREEN_W // 2 - ghost.get_width() // 2 + offset,
                              ty - offset))
            surf.blit(ghost, (SCREEN_W // 2 - ghost.get_width() // 2 - offset,
                              ty + offset))
        title_surf = self.font_title.render(title_text, True, PLAYER_COLOR)
        surf.blit(title_surf, (SCREEN_W // 2 - title_surf.get_width() // 2, ty))

        # Tagline
        tag = self.font_sub.render(tr("tagline"), True, HUD_TEXT)
        surf.blit(tag, (SCREEN_W // 2 - tag.get_width() // 2, 82))

        # Tabs
        self.tab_rects = []
        tab_gap = 5
        side = 12
        tab_width = (SCREEN_W - side * 2 - tab_gap * (len(tabs) - 1)) // len(tabs)
        for index, key in enumerate(tabs):
            rect = pygame.Rect(side + index * (tab_width + tab_gap), 119,
                               tab_width, 41)
            self.tab_rects.append(rect)
            selected = index == active_tab
            fill = (10, 65, 82) if selected else (7, 18, 38)
            border = ENERGY_COLOR if selected else (30, 110, 135)
            pygame.draw.rect(surf, fill, rect, border_radius=7)
            pygame.draw.rect(surf, border, rect, 2 if selected else 1,
                             border_radius=7)
            label = self.font_tab.render(tr(f"menu_tab_{key}"), True,
                                         (255, 225, 245) if selected else HUD_TEXT)
            surf.blit(label, label.get_rect(center=rect.center))

        panel = pygame.Rect(23, 174, SCREEN_W - 46, 516)
        pygame.draw.rect(surf, (3, 10, 27), panel, border_radius=10)
        pygame.draw.rect(surf, (0, 125, 155), panel, 1, border_radius=10)

        # Setting/action rows
        self.row_rects = []
        row_height = 66 if len(rows) <= 6 else 56
        row_y = panel.y + 22
        for index, row in enumerate(rows):
            rect = pygame.Rect(panel.x + 18, row_y + index * row_height,
                               panel.width - 36, row_height - 7)
            self.row_rects.append(rect)
            selected = index == selected_item
            if selected:
                pygame.draw.rect(surf, (15, 55, 73), rect, border_radius=7)
                pygame.draw.rect(surf, ENERGY_COLOR, rect, 2, border_radius=7)
            else:
                pygame.draw.rect(surf, (5, 20, 38), rect, border_radius=7)
                pygame.draw.rect(surf, (15, 60, 78), rect, 1, border_radius=7)

            label_color = (255, 230, 250) if selected else HUD_TEXT
            label = self.font_item.render(row["label"], True, label_color)
            surf.blit(label, (rect.x + 14, rect.y + 9))

            value = row.get("value", "")
            if value:
                value_surface = self.font_value.render(str(value), True,
                                                       ENERGY_COLOR if selected else SCORE_COLOR)
                value_x = rect.right - value_surface.get_width() - 14
                surf.blit(value_surface, (value_x, rect.y + 11))
            elif row.get("action"):
                arrow = self.font_value.render("▶", True,
                                              ENERGY_COLOR if selected else HUD_TEXT)
                surf.blit(arrow, (rect.right - 30, rect.y + 11))

            description = row.get("description", "")
            if description:
                detail = self.font_detail.render(description, True, (105, 155, 180))
                surf.blit(detail, (rect.x + 14, rect.y + 37))

        footer = self.font_detail.render(tr("menu_nav"), True, (115, 175, 195))
        surf.blit(footer, (SCREEN_W // 2 - footer.get_width() // 2, 720))
        mouse = self.font_detail.render("● " + tr("menu_mouse_status"), True,
                                       (80, 210, 255))
        surf.blit(mouse, (SCREEN_W // 2 - mouse.get_width() // 2, 746))

    def hit_test(self, position):
        """Return (kind, index) for a logical-canvas mouse position."""
        for index, rect in enumerate(self.tab_rects):
            if rect.collidepoint(position):
                return ("tab", index)
        for index, rect in enumerate(self.row_rects):
            if rect.collidepoint(position):
                return ("row", index)
        return (None, None)


# ── Game Over / Win screen ────────────────────────────────────────────────────

class OverlayScreen:
    def __init__(self):
        self.font_title = load_font(48, bold=True)
        self.font_sub   = load_font(22)
        self.font_sm    = load_font(16)
        self.anim_tick  = 0
        self.pause_rects = []

    def update(self):
        self.anim_tick += 1

    def draw_game_over(self, surf, score: int, level: int):
        self._draw_backdrop(surf)
        t = self.anim_tick
        # Title
        title = self.font_title.render(tr("system_failure"), True, (255, 60, 60))
        surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, SCREEN_H // 3))
        # Score
        sc = self.font_sub.render(tr("final_stats", score=score, level=level), True, SCORE_COLOR)
        surf.blit(sc, (SCREEN_W // 2 - sc.get_width() // 2, SCREEN_H // 3 + 70))
        # Prompt
        if (t // 30) % 2 == 0:
            p = self.font_sub.render(tr("restart_prompt"), True, ENERGY_COLOR)
            surf.blit(p, (SCREEN_W // 2 - p.get_width() // 2, SCREEN_H // 2 + 50))

    def draw_win(self, surf, score: int, level: int):
        self._draw_backdrop(surf)
        t = self.anim_tick
        pulse = int(220 + 35 * math.sin(t * 0.1))
        title = self.font_title.render(tr("grid_cleared"), True, (60, pulse, 100))
        surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, SCREEN_H // 3))
        sc = self.font_sub.render(tr("score_level", score=score, level=level), True, SCORE_COLOR)
        surf.blit(sc, (SCREEN_W // 2 - sc.get_width() // 2, SCREEN_H // 3 + 70))
        if (t // 30) % 2 == 0:
            p = self.font_sub.render(tr("next_prompt"), True, ENERGY_COLOR)
            surf.blit(p, (SCREEN_W // 2 - p.get_width() // 2, SCREEN_H // 2 + 50))

    def draw_pause(self, surf, muted: bool, selected: int, ai_steps: int,
                   accessibility_label="", controls_label="",
                   power_labels=True):
        self._draw_backdrop(surf)
        title = self.font_title.render(tr("paused"), True, WALL_COLOR)
        surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 150))

        learning = self.font_sm.render(tr("learning_status", steps=ai_steps),
                                       True, (100, 180, 190))
        surf.blit(learning, (SCREEN_W // 2 - learning.get_width() // 2, 220))

        sound = tr("audio_muted") if muted else tr("audio_active")
        options = [
            tr("pause_continue"),
            tr("pause_restart"),
            tr("pause_main_menu"),
            tr("pause_sound", status=sound),
            tr("pause_language"),
            tr("pause_accessibility", status=accessibility_label),
            tr("pause_controls", status=controls_label),
            tr("pause_power_labels", status=(tr("enabled") if power_labels
                                              else tr("disabled"))),
        ]
        self.pause_rects = []
        for index, label in enumerate(options):
            rect = pygame.Rect(105, 257 + index * 35, SCREEN_W - 210, 32)
            self.pause_rects.append(rect)
            color = ENERGY_COLOR if index == selected else HUD_TEXT
            prefix = "▶ " if index == selected else "  "
            if index == selected:
                pygame.draw.rect(surf, (12, 45, 62), rect, border_radius=6)
                pygame.draw.rect(surf, ENERGY_COLOR, rect, 1, border_radius=6)
            text = self.font_sub.render(prefix + label, True, color)
            surf.blit(text, (SCREEN_W // 2 - text.get_width() // 2,
                             261 + index * 35))

        prompt = self.font_sm.render(tr("pause_nav"), True, (130, 170, 190))
        surf.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2, 565))

    def pause_hit_test(self, position):
        for index, rect in enumerate(self.pause_rects):
            if rect.collidepoint(position):
                return index
        return None

    def _draw_backdrop(self, surf):
        overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        overlay.fill((5, 5, 20, 200))
        surf.blit(overlay, (0, 0))
