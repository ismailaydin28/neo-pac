# game.py — NeoPac Core Game Loop & State Machine

import pygame
import math
import logging
import time
import threading
from types import SimpleNamespace
from settings import *
from maze import Maze
from player import Player
from enemy import Enemy
from ui import (HUD, ParticleSystem, ScreenFlash, ScanlineOverlay,
                OverlayScreen, MenuScreen, load_font)
from audio_manager import AudioManager
from localization import tr, toggle_language, current_language, set_language
from learning_ai import load_brains, save_brains, snapshot_brains
from diagnostics import PerformanceMonitor
from profile import ProfileStore
from difficulty import DifficultyManager
from game_modes import GameModeManager
from accessibility import AccessibilityManager
from controls import ControlManager
from powerups import PowerUpManager, POWERUP_BY_KEY
from menu_system import MenuController, TAB_KEYS


class GameState:
    MENU      = "menu"
    PLAYING   = "playing"
    DYING     = "dying"
    GAME_OVER = "game_over"
    WIN       = "win"
    LEVEL_UP  = "level_up"
    PAUSED    = "paused"


class Game:
    """
    Central game controller.
    Owns the maze, player, enemies, HUD, particles, sounds, and the
    state machine that ties everything together.
    """

    def __init__(self, screen: pygame.Surface):
        self.display = screen
        self.screen = pygame.Surface((SCREEN_W, SCREEN_H)).convert()
        self.fullscreen = bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN)
        self.windowed_size = screen.get_size()
        self.clock  = pygame.time.Clock()
        self.logger = logging.getLogger("neopac")
        self.performance = PerformanceMonitor(self.logger)
        self.show_diagnostics = False
        self.last_processing_ms = 0.0
        self.last_frame_ms = 0.0
        self.last_event_ms = 0.0
        self.last_game_ms = 0.0
        self.last_present_ms = 0.0
        self.diagnostics_font = load_font(14)
        self._diagnostics_panel = pygame.Surface((410, 82), pygame.SRCALPHA)
        self._scaled_surface = None
        self._scaled_size = None
        self.shake_frames = 0
        self.shake_strength = 0

        # Independent gameplay modules and persistent user choices.
        self.profile = ProfileStore()
        saved_window_size = self.profile.setting("window_size")
        if isinstance(saved_window_size, list) and len(saved_window_size) == 2:
            self.windowed_size = tuple(saved_window_size)
        set_language(self.profile.setting("language", DEFAULT_LANGUAGE))
        self.difficulty = DifficultyManager(self.profile.setting("difficulty", "normal"))
        self.game_modes = GameModeManager(self.profile.setting("mode", "classic"))
        self.accessibility = AccessibilityManager(
            self.profile.setting("accessibility", "standard")
        )
        self.controls = ControlManager(
            self.profile.setting("control_layout", "wasd_arrows")
        )
        self.powerups = PowerUpManager()
        self.menu_controller = MenuController()
        self.menu_screen = MenuScreen()
        self.show_power_labels = bool(self.profile.setting("power_labels", True))
        self._mouse_visible = None
        self.run_finalized = False

        # UI
        self.hud        = HUD()
        self.particles  = ParticleSystem()
        self.flash      = ScreenFlash()
        self.flash.strength = self.accessibility.current.flash_strength
        self.scanlines  = ScanlineOverlay(SCREEN_W, SCREEN_H)
        self.overlay    = OverlayScreen()

        # Sounds (the game remains playable on systems without audio)
        self.muted = bool(self.profile.setting("muted", False))
        self.audio = AudioManager(self.muted)

        # Game data
        self.level  = 1
        self.score  = 0
        self.lives  = self.difficulty.current.starting_lives
        self.combo  = 0          # consecutive ghost kills in one power session
        self.high_score = self.profile.stat("high_score")
        self.pause_index = 0
        self.ai_brains = load_brains()
        self.ai_save_timer = 0
        self._ai_save_thread = None

        # Maze offset (HUD sits at top; maze starts below)
        self.maze_offset_y = 0  # maze drawn from y=0, HUD at bottom

        self._init_level()
        self.state = GameState.MENU

        # State timers
        self.state_timer = 0

        # Power mode
        self.power_timer = 0

    # ── Level initialisation ──────────────────────────────────────────────────

    def _init_level(self):
        seed = self.game_modes.maze_seed(self.level)
        self.maze    = Maze(seed=seed)
        self.maze.show_power_labels = self.show_power_labels
        self.player  = Player(self.maze)
        num_enemies  = min(2 + self.level - 1, 4)
        self.enemies = [Enemy(i, self.maze, self.ai_brains[i])
                        for i in range(num_enemies)]
        self.power_timer = 0
        self.powerups.reset()
        self.combo = 0
        for enemy in self.enemies:
            enemy.color = self.accessibility.enemy_color(enemy.index)
        self.logger.info(
            "Seviye hazir | seviye=%d tohum=%d dusman=%d hedef=%d",
            self.level, self.maze.seed, len(self.enemies), self.maze.total_dots,
        )

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            frame_started = time.perf_counter()

            # ── Events ──
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._finalize_run()
                    self._save_ai_memory(blocking=True)
                    return
                if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    size = (max(MIN_WINDOW_W, event.w), max(MIN_WINDOW_H, event.h))
                    self.display = pygame.display.set_mode(
                        size, pygame.DOUBLEBUF | pygame.RESIZABLE
                    )
                    self.windowed_size = size
                    self.profile.set_setting("window_size", list(size))
                if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self.controls.refresh_gamepads()
                if event.type == pygame.JOYBUTTONDOWN:
                    self._handle_controller_event(event)
                if event.type == pygame.KEYDOWN:
                    self._handle_keydown(event.key)
                if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    self._handle_mouse_event(event)

            events_finished = time.perf_counter()
            self._sync_mouse_visibility()

            # ── State update & draw ──
            self.screen.fill(DARK_BG)

            if self.state == GameState.MENU:
                self.menu_screen.update()
                self.menu_screen.draw(
                    self.screen,
                    TAB_KEYS,
                    self.menu_controller.tab_index,
                    self.menu_controller.selected_index,
                    self._menu_rows(),
                )

            elif self.state == GameState.PLAYING:
                self._update_playing()
                self._draw_playing()

            elif self.state == GameState.DYING:
                self._update_dying()
                self._draw_playing()

            elif self.state == GameState.GAME_OVER:
                self._draw_playing()
                self.overlay.update()
                self.overlay.draw_game_over(self.screen, self.score, self.level)

            elif self.state == GameState.WIN:
                self._draw_playing()
                self.overlay.update()
                self.overlay.draw_win(self.screen, self.score, self.level)

            elif self.state == GameState.LEVEL_UP:
                self._update_level_up()
                self._draw_playing()

            elif self.state == GameState.PAUSED:
                self._draw_playing()
                self.overlay.update()
                ai_steps = sum(brain.steps for brain in self.ai_brains)
                self.overlay.draw_pause(self.screen, self.muted,
                                        self.pause_index, ai_steps,
                                        self.accessibility.label(current_language()),
                                        self.controls.label(current_language()),
                                        self.show_power_labels)

            # Scanlines on top of everything
            if self.accessibility.current.scanlines:
                self.scanlines.draw(self.screen)
            present_started = time.perf_counter()
            self._present()
            frame_finished = time.perf_counter()
            self.last_processing_ms = (frame_finished - frame_started) * 1000
            self.last_frame_ms = float(dt)
            self.last_event_ms = (events_finished - frame_started) * 1000
            self.last_game_ms = (present_started - events_finished) * 1000
            self.last_present_ms = (frame_finished - present_started) * 1000
            self.performance.record(
                self.last_processing_ms,
                self.last_frame_ms,
                self.state,
                self.power_timer > 0,
                len(self.particles.particles),
                sum(len(brain.q) for brain in self.ai_brains),
                event_ms=self.last_event_ms,
                game_ms=self.last_game_ms,
                present_ms=self.last_present_ms,
            )

    # ── Key handling ──────────────────────────────────────────────────────────

    def _handle_keydown(self, key):
        if key == pygame.K_F3:
            self.show_diagnostics = not self.show_diagnostics
            self.logger.info("F3 performans paneli | acik=%s", self.show_diagnostics)
            return

        if key == pygame.K_F11:
            self._toggle_fullscreen()
            return

        if key == pygame.K_l and self.state != GameState.PLAYING:
            language = toggle_language()
            self.profile.set_setting("language", language)
            pygame.display.set_caption(tr("window_title"))
            return

        if key == pygame.K_m:
            self._toggle_mute()
            return

        if key == pygame.K_ESCAPE:
            if self.state == GameState.MENU:
                self._save_ai_memory(blocking=True)
                pygame.quit()
                raise SystemExit
            if self.state == GameState.PLAYING:
                self.pause_index = 0
                self.state = GameState.PAUSED
            elif self.state == GameState.PAUSED:
                self.state = GameState.PLAYING
            else:
                self.state = GameState.MENU
            return

        if key == pygame.K_p:
            if self.state == GameState.PLAYING:
                self.pause_index = 0
                self.state = GameState.PAUSED
            elif self.state == GameState.PAUSED:
                self.state = GameState.PLAYING
            return

        if key == pygame.K_r and self.state in (
                GameState.PLAYING, GameState.PAUSED, GameState.GAME_OVER):
            self._finalize_run()
            self._full_reset()
            self.state = GameState.PLAYING
            return

        if self.state == GameState.MENU:
            if key in (pygame.K_q, pygame.K_PAGEUP):
                self.menu_controller.move_tab(-1)
            elif key in (pygame.K_e, pygame.K_TAB, pygame.K_PAGEDOWN):
                self.menu_controller.move_tab(1)
            elif key in (pygame.K_UP, pygame.K_w):
                self.menu_controller.move_item(-1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_controller.move_item(1)
            elif key in (pygame.K_LEFT, pygame.K_a):
                if not self._adjust_menu_option(-1):
                    self.menu_controller.move_tab(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                if not self._adjust_menu_option(1):
                    self.menu_controller.move_tab(1)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_menu_option()

        elif self.state == GameState.PLAYING:
            if (key == pygame.K_SPACE and self.game_modes.current.dash_allowed
                    and self.player.request_dash()):
                self._play_sound('dash')

        elif self.state == GameState.PAUSED:
            if key in (pygame.K_UP, pygame.K_w):
                self.pause_index = (self.pause_index - 1) % 8
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.pause_index = (self.pause_index + 1) % 8
            elif key == pygame.K_RETURN:
                self._activate_pause_option()

        elif self.state in (GameState.GAME_OVER,):
            if key == pygame.K_RETURN:
                self._full_reset()
                self.state = GameState.PLAYING
        elif self.state == GameState.WIN:
            if key == pygame.K_RETURN:
                self.level += 1
                self._init_level()
                self.state = GameState.PLAYING

    # ── Tabbed main menu ─────────────────────────────────────────────────────

    def _menu_rows(self):
        """Build localized rows for the active tab from live settings."""
        tab = self.menu_controller.tab_key

        def row(key, value="", action=False, description=True):
            return {
                "key": key,
                "label": tr(f"menu_{key}"),
                "value": value,
                "action": action,
                "description": tr(f"menu_{key}_desc") if description else "",
            }

        if tab == "play":
            return [row("start", action=True), row("daily_start", action=True),
                    row("quit", action=True)]
        if tab == "game":
            return [
                row("mode", self.game_modes.label(current_language())),
                row("difficulty", self.difficulty.label(current_language())),
                row("power_labels", tr("enabled") if self.show_power_labels
                    else tr("disabled")),
            ]
        if tab == "display":
            return [
                row("accessibility", self.accessibility.label(current_language())),
                row("fullscreen", tr("enabled") if self.fullscreen else tr("disabled")),
                row("language", tr("language_tr") if current_language() == "tr"
                    else tr("language_en")),
                row("diagnostics", tr("enabled") if self.show_diagnostics
                    else tr("disabled")),
            ]
        if tab == "controls":
            return [
                row("control_layout", self.controls.label(current_language())),
                row("audio", tr("disabled") if self.muted else tr("enabled")),
                row("mouse_status", tr("enabled")),
            ]

        stats = self.profile.data["stats"]
        return [
            row("high_score", f"{stats.get('high_score', 0):,}", description=False),
            row("games_played", f"{stats.get('games_played', 0):,}", description=False),
            row("highest_level", f"{stats.get('highest_level', 1):,}", description=False),
            row("dots_collected", f"{stats.get('dots_collected', 0):,}", description=False),
            row("sentinels_eaten", f"{stats.get('sentinels_eaten', 0):,}", description=False),
            row("total_score", f"{stats.get('total_score', 0):,}", description=False),
        ]

    def _adjust_menu_option(self, step):
        """Change the selected setting; return False for non-setting rows."""
        key = self.menu_controller.selected_key
        if key == "mode":
            self.game_modes.cycle(step)
            self.profile.set_setting("mode", self.game_modes.current.key)
        elif key == "difficulty":
            self.difficulty.cycle(step)
            self.profile.set_setting("difficulty", self.difficulty.current.key)
        elif key == "power_labels":
            self.show_power_labels = not self.show_power_labels
            self.maze.show_power_labels = self.show_power_labels
            self.profile.set_setting("power_labels", self.show_power_labels)
        elif key == "accessibility":
            self._cycle_accessibility(step)
        elif key == "fullscreen":
            self._toggle_fullscreen()
        elif key == "language":
            language = toggle_language()
            self.profile.set_setting("language", language)
            pygame.display.set_caption(tr("window_title"))
        elif key == "diagnostics":
            self.show_diagnostics = not self.show_diagnostics
            self.logger.info("F3 performans paneli | acik=%s", self.show_diagnostics)
        elif key == "control_layout":
            self.controls.cycle(step)
            self.profile.set_setting("control_layout", self.controls.key)
        elif key == "audio":
            self._toggle_mute()
        else:
            return False
        return True

    def _activate_menu_option(self):
        key = self.menu_controller.selected_key
        if key == "start":
            self._full_reset()
            self.state = GameState.PLAYING
        elif key == "daily_start":
            self.game_modes.select("daily")
            self.profile.set_setting("mode", self.game_modes.current.key)
            self._full_reset()
            self.state = GameState.PLAYING
        elif key == "quit":
            self._save_ai_memory(blocking=True)
            pygame.quit()
            raise SystemExit
        else:
            self._adjust_menu_option(1)

    def _handle_mouse_event(self, event):
        if self.state not in (GameState.MENU, GameState.PAUSED):
            return
        position = self._display_to_logical(event.pos)
        if position is None:
            return

        if self.state == GameState.MENU:
            kind, index = self.menu_screen.hit_test(position)
            if event.type == pygame.MOUSEMOTION:
                if kind == "row":
                    self.menu_controller.select_item(index)
                return
            if event.button in (4, 5):
                self.menu_controller.move_item(-1 if event.button == 4 else 1)
                return
            if kind == "tab" and event.button == 1:
                self.menu_controller.select_tab(index)
            elif kind == "row":
                self.menu_controller.select_item(index)
                if event.button == 1:
                    self._activate_menu_option()
                elif event.button == 3:
                    self._adjust_menu_option(-1)
            return

        pause_index = self.overlay.pause_hit_test(position)
        if pause_index is None:
            return
        self.pause_index = pause_index
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._activate_pause_option()

    def _display_to_logical(self, position):
        """Map letterboxed window coordinates to the 672×804 canvas."""
        dw, dh = self.display.get_size()
        scale = min(dw / SCREEN_W, dh / SCREEN_H)
        target_w = max(1, int(SCREEN_W * scale))
        target_h = max(1, int(SCREEN_H * scale))
        offset_x = (dw - target_w) // 2
        offset_y = (dh - target_h) // 2
        x, y = position
        if not (offset_x <= x < offset_x + target_w
                and offset_y <= y < offset_y + target_h):
            return None
        return (int((x - offset_x) / scale), int((y - offset_y) / scale))

    def _sync_mouse_visibility(self):
        visible = self.state in (GameState.MENU, GameState.PAUSED)
        if visible != self._mouse_visible:
            pygame.mouse.set_visible(visible)
            self._mouse_visible = visible

    def _handle_controller_event(self, event):
        if self.state == GameState.MENU and event.button in (4, 5):
            self.menu_controller.move_tab(-1 if event.button == 4 else 1)
            return
        if event.button in (6, 7):
            if self.state == GameState.PLAYING:
                self.pause_index = 0
                self.state = GameState.PAUSED
            elif self.state == GameState.PAUSED:
                self.state = GameState.PLAYING
        elif event.button == 0:
            if self.state == GameState.MENU:
                self._activate_menu_option()
            elif (self.state == GameState.PLAYING
                  and self.game_modes.current.dash_allowed
                  and self.player.request_dash()):
                self._play_sound('dash')
    # ── Playing update ────────────────────────────────────────────────────────

    def _update_playing(self):
        keys = pygame.key.get_pressed()

        if self.game_modes.update():
            self.lives = 0
            self.state = GameState.GAME_OVER
            self.overlay.anim_tick = 0
            self.logger.info("Sure doldu | mod=%s puan=%d",
                             self.game_modes.current.key, self.score)
            self._finalize_run()
            return
        self.profile.increment("play_frames")

        ended_powers = self.powerups.update()
        self.power_timer = self.powerups.remaining("overclock")
        if "overclock" in ended_powers:
            self._end_power_mode()

        # Player
        dx, dy = self.controls.direction(keys)
        self.player.set_direction(dx, dy)
        if self.powerups.active("chain_dash"):
            self.player.dash_cooldown = min(self.player.dash_cooldown, 10)
        self.player.update()

        # Collectibles
        score_earned, power_kind = self.player.collect()
        if score_earned:
            self.score += score_earned
            self.high_score = max(self.high_score, self.score)
            self.profile.increment("dots_collected")
            px, py = int(self.player.x), int(self.player.y)
            if power_kind:
                self._activate_powerup(power_kind, px, py)
                self._play_sound('power')
            else:
                self._play_sound('dot')
                self._burst(px, py, DOT_COLOR, count=4, speed=1.5, life=15)

        if self.powerups.active("magnet"):
            attracted = self.maze.collect_dots_near(
                self.player.tile_r, self.player.tile_c, radius=3
            )
            if attracted:
                gained = len(attracted) * DOT_SCORE
                self.score += gained
                self.high_score = max(self.high_score, self.score)
                self.profile.increment("dots_collected", len(attracted))

        enemy_target = self.player
        if self.powerups.active("decoy") and self.powerups.decoy_tile:
            dr, dc = self.powerups.decoy_tile
            enemy_target = SimpleNamespace(tile_r=dr, tile_c=dc, dir_x=0, dir_y=0)

        # Enemies
        frozen = self.powerups.active("freeze")
        for enemy in self.enemies:
            if not frozen:
                enemy.update(
                    enemy_target,
                    self.level,
                    speed_scale=self.difficulty.current.enemy_speed,
                    exploration_scale=self.difficulty.current.ai_exploration_scale,
                )
                if enemy.ability.just_activated:
                    self._play_sound("sentinel_alert")
            if enemy.collides_with_player(self.player):
                if enemy.mode == Enemy.MODE_SCARED:
                    self._eat_ghost(enemy)
                elif not frozen and self.player.invincible_frames == 0:
                    if self.powerups.consume_shield():
                        self.player.invincible_frames = 90
                        self.flash.trigger((80, 210, 255), frames=8)
                    else:
                        self._kill_player(enemy)
                        return

        self.ai_save_timer += 1
        if self.ai_save_timer >= AI_AUTOSAVE_FRAMES:
            self._save_ai_memory()

        # HUD
        self.hud.update()
        self.particles.update()
        self.flash.update()

        # Win condition
        if self.maze.all_dots_collected():
            self._play_sound('level_up')
            self.profile.maximum("highest_level", self.level)
            if self.game_modes.current.endless:
                self.level += 1
                self._init_level()
                self.state = GameState.PLAYING
            else:
                self.state = GameState.WIN
                self.overlay.anim_tick = 0

    # ── Dying update ──────────────────────────────────────────────────────────

    def _update_dying(self):
        self.state_timer -= 1
        self.particles.update()
        self.flash.update()
        self.hud.update()
        if self.state_timer <= 0:
            if self.lives <= 0:
                self.state = GameState.GAME_OVER
                self.overlay.anim_tick = 0
                self._finalize_run()
            else:
                # Respawn
                self.player.reset(invincible=True)
                for e in self.enemies:
                    e.reset()
                self.state = GameState.PLAYING

    # ── Level-up transition ───────────────────────────────────────────────────

    def _update_level_up(self):
        self.state_timer -= 1
        self.particles.update()
        self.flash.update()
        self.hud.update()
        if self.state_timer <= 0:
            self.state = GameState.WIN

    # ── Power mode ────────────────────────────────────────────────────────────

    def _activate_powerup(self, key, px, py):
        definition = self.powerups.activate(
            key,
            (self.player.tile_r, self.player.tile_c),
            duration_scale=self.difficulty.current.power_scale,
        )
        if definition.key == "overclock":
            self.power_timer = self.powerups.remaining("overclock")
            self.combo = 0
            for enemy in self.enemies:
                enemy.frighten(self.power_timer)
        self.flash.trigger(definition.color, frames=10)
        self._trigger_shake(4, 2)
        self._burst(px, py, definition.color, count=20, speed=4, life=40)
        self.logger.info("Guc alindi | tur=%s sure=%d", definition.key,
                         self.powerups.remaining(definition.key))

    def _activate_power_mode(self, px, py):
        """Compatibility wrapper for the original Overclock tests/API."""
        self.powerups.activate(
            "overclock",
            (self.player.tile_r, self.player.tile_c),
            duration_scale=self.difficulty.current.power_scale,
        )
        self.power_timer = self.powerups.remaining("overclock")
        self.combo = 0
        for e in self.enemies:
            e.frighten(self.power_timer)
        self.flash.trigger(ENERGY_COLOR, frames=10)
        self._burst(px, py, POWER_COLOR, count=20, speed=4, life=40)
        self.logger.info("Asiri guc basladi | sure=%d", self.power_timer)

    def _end_power_mode(self):
        self.powerups.timers["overclock"] = 0
        self.power_timer = 0
        for e in self.enemies:
            if e.mode == Enemy.MODE_SCARED:
                e.end_fright()
            elif e.mode == Enemy.MODE_RESPAWNING:
                e.cancel_pending_power()
        self.combo = 0
        self.logger.info("Asiri guc sona erdi")

    def _eat_ghost(self, enemy: Enemy):
        pts = GHOST_SCORES[min(self.combo, len(GHOST_SCORES) - 1)]
        self.score += pts
        self.high_score = max(self.high_score, self.score)
        self.combo += 1
        self.profile.increment("sentinels_eaten")
        self.profile.maximum("best_combo", self.combo)
        self._play_sound('ghost_eat')
        ex, ey = int(enemy.x), int(enemy.y)
        self._burst(ex, ey, enemy.color, count=16, speed=4, life=35)
        self.flash.trigger((80, 80, 255), frames=8)
        self._trigger_shake(5, 3)
        self.hud.show_combo(f"+{pts}")
        enemy.give_reward(-120.0)
        enemy.respawn_after_eaten(self.power_timer)
        self.logger.info(
            "Sentinel yenildi | id=%d puan=%d zincir=%d kalan_guc=%d",
            enemy.index, pts, self.combo, self.power_timer,
        )

    # ── Player death ──────────────────────────────────────────────────────────

    def _kill_player(self, killer=None):
        self.lives -= 1
        if killer is not None:
            killer.give_reward(150.0)
            for enemy in self.enemies:
                if enemy is not killer:
                    enemy.give_reward(12.0)
        self._end_power_mode()
        self.powerups.reset()
        self._play_sound('death')
        px, py = int(self.player.x), int(self.player.y)
        self._burst(px, py, PLAYER_COLOR, count=25, speed=5, life=50)
        self.flash.trigger((255, 60, 60), frames=20)
        self._trigger_shake(12, 5)
        self.state = GameState.DYING
        self.state_timer = DEATH_FREEZE_FRAMES
        self.logger.info(
            "Oyuncu elendi | katil=%s kalan_can=%d seviye=%d puan=%d",
            getattr(killer, "index", None), self.lives, self.level, self.score,
        )

    # ── Full reset (new game) ─────────────────────────────────────────────────

    def _full_reset(self):
        self.game_modes.begin_run(FPS)
        self.run_finalized = False
        self.profile.increment("games_played")
        self.level  = 1
        self.score  = 0
        self.lives = self.difficulty.current.starting_lives
        if self.game_modes.current.one_life:
            self.lives = 1
        self.combo  = 0
        self._init_level()

    def _activate_pause_option(self):
        if self.pause_index == 0:       # continue
            self.state = GameState.PLAYING
        elif self.pause_index == 1:     # restart
            self._finalize_run()
            self._full_reset()
            self.state = GameState.PLAYING
        elif self.pause_index == 2:     # main menu
            self._finalize_run()
            self._save_ai_memory()
            self.state = GameState.MENU
        elif self.pause_index == 3:     # sound
            self._toggle_mute()
        elif self.pause_index == 4:     # language
            language = toggle_language()
            self.profile.set_setting("language", language)
            pygame.display.set_caption(tr("window_title"))
        elif self.pause_index == 5:     # accessibility
            self._cycle_accessibility()
        elif self.pause_index == 6:     # controls
            self.controls.cycle()
            self.profile.set_setting("control_layout", self.controls.key)
        elif self.pause_index == 7:     # visible power names
            self.show_power_labels = not self.show_power_labels
            self.maze.show_power_labels = self.show_power_labels
            self.profile.set_setting("power_labels", self.show_power_labels)

    def _cycle_accessibility(self, step=1):
        self.accessibility.cycle(step)
        self.profile.set_setting("accessibility", self.accessibility.current.key)
        self.flash.strength = self.accessibility.current.flash_strength
        for enemy in getattr(self, "enemies", []):
            enemy.color = self.accessibility.enemy_color(enemy.index)

    def _finalize_run(self):
        if self.run_finalized or self.profile.stat("games_played") == 0:
            return
        self.run_finalized = True
        self.profile.maximum("high_score", self.high_score)
        self.profile.maximum("highest_level", self.level)
        self.profile.increment("total_score", self.score)
        if self.game_modes.current.daily_seed:
            self.profile.record_daily(self.game_modes.daily_key(), self.score)
        self.profile.save()

    def _burst(self, x, y, color, count=12, speed=3.0, life=30):
        if self.accessibility.current.low_motion:
            count = max(1, count // 4)
            speed *= 0.55
        self.particles.burst(x, y, color, count=count, speed=speed, life=life)

    def _trigger_shake(self, frames, strength):
        if not self.accessibility.current.screen_shake:
            return
        self.shake_frames = max(self.shake_frames, frames)
        self.shake_strength = max(self.shake_strength, strength)

    def _save_ai_memory(self, blocking=False):
        """Persist learning without serializing JSON on an active game frame."""
        self.profile.maximum("high_score", self.high_score)
        self.profile.maximum("highest_level", self.level)
        self.profile.save()
        self.ai_save_timer = 0

        if blocking:
            if self._ai_save_thread and self._ai_save_thread.is_alive():
                self._ai_save_thread.join()
            started = time.perf_counter()
            saved = save_brains(self.ai_brains)
            elapsed_ms = (time.perf_counter() - started) * 1000
            self.logger.info(
                "AI bellegi kaydi | basarili=%s sure=%.1fms durum=%d adim=%d tur=beklemeli",
                saved,
                elapsed_ms,
                sum(len(brain.q) for brain in self.ai_brains),
                sum(brain.steps for brain in self.ai_brains),
            )
            return saved

        if self._ai_save_thread and self._ai_save_thread.is_alive():
            self.logger.info("AI bellegi kaydi zaten arka planda calisiyor")
            return False

        started = time.perf_counter()
        snapshot = snapshot_brains(self.ai_brains)
        snapshot_ms = (time.perf_counter() - started) * 1000
        states = sum(len(brain.q) for brain in snapshot)
        steps = sum(brain.steps for brain in snapshot)
        self._ai_save_thread = threading.Thread(
            target=self._write_ai_snapshot,
            args=(snapshot, states, steps, snapshot_ms),
            name="neopac-ai-save",
            daemon=True,
        )
        self._ai_save_thread.start()
        self.logger.info(
            "AI bellegi arka plana alindi | kopya=%.1fms durum=%d adim=%d",
            snapshot_ms, states, steps,
        )
        return True

    def _write_ai_snapshot(self, snapshot, states, steps, snapshot_ms):
        started = time.perf_counter()
        saved = save_brains(snapshot)
        write_ms = (time.perf_counter() - started) * 1000
        self.logger.info(
            "AI bellegi kaydi | basarili=%s yazma=%.1fms kopya=%.1fms "
            "durum=%d adim=%d tur=arka_plan",
            saved, write_ms, snapshot_ms, states, steps,
        )

    # ── Sound ─────────────────────────────────────────────────────────────────

    def _toggle_mute(self):
        self.muted = self.audio.toggle()
        self.profile.set_setting("muted", self.muted)

    def _play_sound(self, name: str):
        self.audio.play(name)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def _draw_playing(self):
        oy = self.maze_offset_y
        # Maze (walls + dots)
        self.maze.draw(self.screen, oy)
        # Player trail + body
        self.player.draw(self.screen, oy)
        # Enemies
        for e in self.enemies:
            e.draw(self.screen, oy)
        if self.powerups.active("decoy") and self.powerups.decoy_tile:
            dr, dc = self.powerups.decoy_tile
            dx, dy = self.maze.tile_center(dr, dc)
            pulse = 7 + int(2 * math.sin(self.maze.anim_tick * 0.18))
            pygame.draw.circle(self.screen, (180, 100, 255), (dx, dy + oy), pulse, 2)
            pygame.draw.line(self.screen, (220, 180, 255),
                             (dx - 4, dy + oy), (dx + 4, dy + oy), 1)
        # Particles (world-space)
        self._draw_particles_with_offset(oy)
        # Screen flash
        self.flash.draw(self.screen)
        # HUD
        active_status = ""
        for key in ("freeze", "magnet", "decoy", "chain_dash"):
            if self.powerups.active(key):
                definition = POWERUP_BY_KEY[key]
                active_status = (definition.label_tr if current_language() == "tr"
                                 else definition.label_en)
                break
        if self.powerups.shield_hits and not active_status:
            active_status = tr("shield", count=self.powerups.shield_hits)
        time_seconds = None
        if self.game_modes.frames_remaining is not None:
            time_seconds = (self.game_modes.frames_remaining + FPS - 1) // FPS
        self.hud.draw(
            self.screen,
            score=self.score,
            lives=self.lives,
            level=self.level,
            high_score=self.high_score,
            power_timer=self.power_timer,
            dash_cooldown=self.player.dash_cooldown,
            muted=self.muted,
            power_duration=max(1, int(POWER_DURATION * self.difficulty.current.power_scale)),
            status_text=active_status,
            time_seconds=time_seconds,
            shield_count=self.powerups.shield_hits,
        )
        # Power mode edge glow
        if self.power_timer > 0:
            self._draw_power_edge_glow()
        if self.show_diagnostics:
            self._draw_diagnostics()

    def _draw_particles_with_offset(self, oy):
        """Particles store world-y; apply offset when drawing."""
        for p in self.particles.particles:
            p.draw(self.screen)

    def _draw_power_edge_glow(self):
        """Pulsing neon border when overclock is active."""
        t = self.maze.anim_tick
        brightness = 0.55 + 0.35 * ((math.sin(t * 0.15) + 1.0) / 2.0)
        color = tuple(int(channel * brightness) for channel in ENERGY_COLOR)
        pygame.draw.rect(
            self.screen,
            color,
            (0, 0, SCREEN_W, ROWS * TILE_SIZE),
            4,
        )

    def _draw_diagnostics(self):
        """Small F3 overlay for checking slowdowns during real gameplay."""
        ai_states = sum(len(brain.q) for brain in self.ai_brains)
        lines = (
            f"FPS {self.clock.get_fps():5.1f} | kare {self.last_frame_ms:4.1f} ms",
            f"olay {self.last_event_ms:4.1f} | oyun {self.last_game_ms:4.1f} | sunum {self.last_present_ms:4.1f} ms",
            f"islem {self.last_processing_ms:4.1f} ms | parcacik {len(self.particles.particles)}",
            f"AI {ai_states} | {self.game_modes.current.key}/{self.difficulty.current.key} | {self.maze.seed}",
        )
        panel = self._diagnostics_panel
        panel.fill((0, 0, 0, 0))
        panel.fill((2, 8, 20, 205))
        pygame.draw.rect(panel, (*WALL_COLOR, 190), panel.get_rect(), 1)
        for index, line in enumerate(lines):
            label = self.diagnostics_font.render(line, True, (190, 245, 255))
            panel.blit(label, (7, 4 + index * 19))
        self.screen.blit(panel, (7, 7))

    # ── Resolution-independent presentation ────────────────────────────────────────────────

    def _present(self):
        """Scale the logical canvas to any window, including 4K, letterboxed."""
        self.display = pygame.display.get_surface()
        dw, dh = self.display.get_size()
        scale = min(dw / SCREEN_W, dh / SCREEN_H)
        target_w = max(1, int(SCREEN_W * scale))
        target_h = max(1, int(SCREEN_H * scale))
        target_size = (target_w, target_h)
        if target_size == self.screen.get_size():
            output_surface = self.screen
            if self._scaled_size != target_size:
                self._scaled_size = target_size
                self._scaled_surface = None
                self.logger.info("Goruntu dogrudan sunuluyor | boyut=%dx%d", target_w, target_h)
        else:
            if self._scaled_surface is None or self._scaled_size != target_size:
                self._scaled_surface = pygame.Surface(target_size).convert()
                self._scaled_size = target_size
                self.logger.info("Goruntu olcegi degisti | boyut=%dx%d", target_w, target_h)
            pygame.transform.scale(self.screen, target_size, self._scaled_surface)
            output_surface = self._scaled_surface
        self.display.fill(BLACK)
        offset_x = 0
        offset_y = 0
        if self.shake_frames > 0 and self.accessibility.current.screen_shake:
            offset_x = int(math.sin(self.shake_frames * 2.31) * self.shake_strength)
            offset_y = int(math.cos(self.shake_frames * 1.73) * self.shake_strength)
            self.shake_frames -= 1
            if self.shake_frames == 0:
                self.shake_strength = 0
        self.display.blit(
            output_surface,
            ((dw - target_w) // 2 + offset_x, (dh - target_h) // 2 + offset_y),
        )
        pygame.display.flip()

    def _toggle_fullscreen(self):
        if self.fullscreen:
            self.display = pygame.display.set_mode(
                self.windowed_size, pygame.DOUBLEBUF | pygame.RESIZABLE,
                vsync=0,
            )
            self.fullscreen = False
            self.profile.set_setting("fullscreen", False)
        else:
            self.windowed_size = pygame.display.get_surface().get_size()
            self.profile.set_setting("window_size", list(self.windowed_size))
            try:
                self.display = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H),
                    pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.SCALED,
                    vsync=0,
                )
                self.logger.info(
                    "Tam ekran donanim olcekleme | mantiksal=%s fiziksel=%s",
                    self.display.get_size(), pygame.display.get_window_size(),
                )
            except pygame.error as exc:
                self.logger.warning(
                    "Donanim olcekleme kullanilamadi, yazilim yedegi | hata=%s", exc
                )
                self.display = pygame.display.set_mode(
                    (0, 0), pygame.DOUBLEBUF | pygame.FULLSCREEN, vsync=0
                )
            self.fullscreen = True
            self.profile.set_setting("fullscreen", True)
        self._scaled_surface = None
        self._scaled_size = None
