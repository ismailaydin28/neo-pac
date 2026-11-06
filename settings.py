# settings.py — NeoPac Global Configuration
# All constants and configuration values live here.

# ─── Window ───────────────────────────────────────────────────────────────────
SCREEN_TITLE  = "NeoPac — Siberpunk Labirent"
TILE_SIZE     = 24          # pixels per grid cell
COLS          = 28          # maze width in tiles
ROWS          = 31          # maze height in tiles
SCREEN_W      = COLS * TILE_SIZE          # 672
SCREEN_H      = ROWS * TILE_SIZE + 60    # 744 + HUD strip
FPS           = 60
MIN_WINDOW_W  = 420
MIN_WINDOW_H  = 503
DEFAULT_LANGUAGE = "tr"

# ─── Colors (neon palette) ────────────────────────────────────────────────────
BLACK         = (  0,   0,   0)
DARK_BG       = (  5,   5,  20)          # almost-black navy
WALL_COLOR    = (  0, 220, 255)          # cyan neon
WALL_INNER    = (  0,  40,  60)          # dark wall fill
DOT_COLOR     = (180, 230, 255)          # ice-blue energy orb
POWER_COLOR   = (255,  60, 220)          # magenta overclock core
PORTAL_COLOR  = (100, 255, 100)          # green portal

PLAYER_COLOR  = ( 60, 180, 255)          # electric blue avatar
PLAYER_TRAIL  = ( 20,  80, 150)          # dim trail

ENEMY_COLORS  = [
    (255,  80,  80),   # red sentinel
    (255, 160,  40),   # orange drone
    ( 80, 255, 220),   # teal hunter
    (220,  80, 255),   # violet stalker
]
ENEMY_SCARED  = ( 40,  40, 180)          # dark-blue when vulnerable
ENEMY_BLINK   = (220, 220, 255)          # blink color near end

HUD_BG        = (  8,   8,  30)
HUD_TEXT      = (  0, 255, 200)          # neon green-cyan
SCORE_COLOR   = (255, 220,   0)          # gold score digits
LIFE_COLOR    = ( 60, 180, 255)
ENERGY_COLOR  = (255,  60, 220)

# ─── Gameplay ─────────────────────────────────────────────────────────────────
PLAYER_SPEED        = 3          # pixels per frame (sub-tile movement)
PLAYER_DASH_SPEED   = 7
PLAYER_DASH_FRAMES  = 18         # frames dash lasts
PLAYER_DASH_COOLDOWN= 90         # frames between dashes

ENEMY_BASE_SPEED    = 1.6        # pixels per frame
ENEMY_SPEED_STEP    = 0.15       # added per level
ENEMY_MAX_SPEED     = 3.2        # keep later levels fast but fair
ENEMY_SCARED_SPEED  = 1.1
ENEMY_SCATTER_TICKS = 420        # frames in scatter mode
ENEMY_CHASE_TICKS   = 800        # frames in chase mode

# Lightweight Q-learning (kept dependency-free for low-end systems)
AI_LEARNING_RATE    = 0.18
AI_DISCOUNT         = 0.90
AI_EXPLORATION      = 0.06       # live exploration chance
AI_AUTOSAVE_FRAMES  = 3600       # save learned policies every ~60 seconds

POWER_DURATION      = 480        # frames (~8 s at 60 fps)
POWER_BLINK_START   = 120        # frames before end when blinking starts
ENEMY_RESPAWN_FRAMES = 45        # eaten sentinel is eyes-only for 0.75 seconds

# Diagnostics
SLOW_FRAME_MS       = 25.0       # processing time threshold written to log
PERF_REPORT_SECONDS = 10         # periodic performance summary interval

STARTING_LIVES      = 3
DEATH_FREEZE_FRAMES = 90         # pause after dying
RESPAWN_INVINCIBLE_FRAMES = 120  # brief protection after losing a life

DOT_SCORE           = 10
POWER_SCORE         = 50
GHOST_SCORES        = [200, 400, 800, 1600]   # consecutive ghost kills

# ─── Maze layout key ─────────────────────────────────────────────────────────
# 1 = wall, 0 = dot, 7 = power pellet, 8 = portal, 9 = empty (no dot)
MAZE_LAYOUT = [
    "1111111111111111111111111111",
    "1000000001100000001100000001",
    "1011011101100111101100111101",  # row 2
    "1711011101100111101100111701",  # row 3: power pellets
    "1011011101100111101100111101",
    "1000000000000000000000000001",
    "1011011011101111011101101101",  # row 6
    "1011011011101111011101101101",
    "1000001100001111000011000001",
    "1111011111 0      0 11111011",  # intentionally blank center cols (ghost house)
    "1111011111 0 1111 0 11111011",
    "          0 1    1 0        ",  # ghost house row  (cols 0-11,16-27 open)
    "1111011111 0 1111 1 11111011",
    "1111011111 0      0 11111011",
    "8000000000000000000000000008",  # row 14: working tunnel portals
    "1011011101100111101100111101",
    "1011011101100111101100111701",
    "1000110000011111100000110001",  # sealed former unreachable center pocket
    "1110111011101111011101110111",
    "1110111011101111011101110111",
    "1000000000000000000000000001",
    "1011011101100111101100111101",
    "1011011101100111101100111101",
    "1000000001100000001100000001",
    "1011111101111111111101111101",
    "1011111101111111111101111101",
    "1000001000000110000001000001",
    "1110001011101111011101000111",
    "1110001011101111011101000111",
    "1000000000000000000000000001",
    "1111111111111111111111111111",
]

# Portal pairs: (row, col) → (row, col)  — generated maze tunnel exits
PORTAL_ROW = ROWS // 2
PORTALS = {
    (PORTAL_ROW, 0): (PORTAL_ROW, COLS - 1),
    (PORTAL_ROW, COLS - 1): (PORTAL_ROW, 0),
}
