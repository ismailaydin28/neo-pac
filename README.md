# NeoPac

**A neon cyberpunk maze runner with procedural levels, persistent learning AI, six game modes, accessibility presets, and a fully keyboard/mouse-friendly interface.**

[Türkçe README](README_TR.md)

NeoPac is a Python/Pygame arcade game inspired by classic maze-chase gameplay. It expands the formula with procedurally generated mazes, personality-driven Sentinels, persistent tabular Q-learning, multiple power cores, daily challenges, performance diagnostics, localization, and resolution-independent rendering up to 4K.

The game starts in Turkish by default. Change the language from `Display → Language` or press `L` while outside active gameplay.

## Highlights

- A new connected and completable procedural maze on every level
- Six distinct game modes and four difficulty presets
- Six named power cores with clearly visible labels
- Four Sentinel personalities with unique targets, rewards, penalties, and special abilities
- Persistent Q-learning memory that continues improving during play
- Turkish and English interfaces
- Tabbed settings menu controlled by mouse, WASD, arrow keys, or gamepad
- Full pause menu with restart, main-menu, sound, language, accessibility, controls, and power-label settings
- Window resizing, aspect-ratio preservation, accelerated fullscreen scaling, and 4K support
- Reduced-flash, colorblind, and low-motion accessibility presets
- Separate rotating logs for gameplay systems
- Built-in live performance panel and automated regression tests

## Requirements

| Component | Requirement |
|---|---|
| Python | 3.10 or newer |
| Pygame | 2.6 or newer |
| Operating system | Linux, Windows, or macOS supported by Pygame |

## Quick Start

```bash
git clone https://github.com/ismailaydin28/neo-pac.git
cd neo-pac

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

python3 main.py
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\activate
```

## Gameplay Controls

| Input | Action |
|---|---|
| `W` / `↑` | Move up |
| `A` / `←` | Move left |
| `S` / `↓` | Move down |
| `D` / `→` | Move right |
| `Space` | Dash |
| `P` / `Esc` | Pause or resume |
| `R` | Restart the current run |
| `M` | Toggle audio |
| `F3` | Toggle the performance panel |
| `F11` | Toggle fullscreen |
| `L` | Toggle Turkish/English outside active gameplay |

The selected keyboard layout can be changed to `WASD + Arrows`, `Arrows Only`, or `IJKL`.

### Gamepad

- Left stick or D-pad: movement
- Primary button: dash or confirm
- Start/Select: pause or resume
- Shoulder buttons: change main-menu tabs

Gamepads are detected again when they are connected or disconnected.

## Tabbed Main Menu

The main menu is split into five focused tabs:

| Tab | Contents |
|---|---|
| Play | Start game, start the daily maze, quit |
| Game | Game mode, difficulty, power-name visibility |
| Display | Accessibility, fullscreen, language, performance panel |
| Controls | Keyboard layout, audio, mouse status |
| Stats | High score, games played, highest level, collected energy, eaten Sentinels, total score |

### Menu Navigation

| Input | Action |
|---|---|
| `Q` / `E` or `Tab` | Change tab |
| `W` / `S` or `↑` / `↓` | Select a row |
| `A` / `D` or `←` / `→` | Change the selected value |
| `Enter` / `Space` | Confirm or activate |
| Left mouse button | Select a tab/row or advance a setting |
| Right mouse button | Move a setting to the previous value |
| Mouse wheel | Move through rows |

The mouse is visible in the main and pause menus, then hides automatically during gameplay.

## Game Modes

| Mode | Rules |
|---|---|
| Classic | Standard level progression |
| Time Attack | Score as much as possible before the 120-second timer expires |
| One Life | The run starts with a single life |
| No Dash | Dash is disabled |
| Daily Maze | Uses a stable date-based seed so the same day produces the same maze |
| Endless | Clearing a maze immediately continues to the next level |

## Difficulty Presets

Difficulty changes several systems together instead of only increasing movement speed.

| Difficulty | Lives | Sentinel speed | Power duration | AI exploration |
|---|---:|---:|---:|---:|
| Casual | 5 | 82% | 130% | 125% |
| Normal | 3 | 100% | 100% | 100% |
| Hard | 2 | 116% | 82% | 72% |
| Cyber Nightmare | 1 | 130% | 65% | 45% |

Lower AI exploration at high difficulty makes the trained policies more consistent and less random.

## Collectibles and Power Cores

| Object | Score | Effect |
|---|---:|---|
| Energy orb | 10 | Standard maze collectible |
| Power core | 50 | Activates one of six special abilities |
| Portal | — | Teleports the player between tunnel exits |

Every procedural maze contains exactly one of each power core. Their names are displayed directly above them, so the player never has to memorize colors. Labels can be toggled from `Game → Power Labels` or from the pause menu.

| Power | Effect |
|---|---|
| Overclock | Makes Sentinels vulnerable and enables combo scoring |
| Shield | Blocks one enemy hit; up to two charges can be held |
| Time Freeze | Temporarily stops Sentinel movement |
| Energy Magnet | Collects nearby energy orbs automatically |
| Decoy | Redirects Sentinel targeting to a false player position |
| Chain Dash | Greatly reduces dash cooldown |

Eating vulnerable Sentinels awards a combo sequence of `200`, `400`, `800`, and `1600` points.

## Sentinel AI

Each Sentinel has a distinct personality, target strategy, learning table, and reward model.

| Sentinel | Personality | Primary behavior |
|---|---|---|
| Red | Chaser | Pursues the player through the shortest valid route |
| Orange | Ambusher | Targets a position ahead of the player's movement |
| Teal | Flanker | Approaches from a side target to surround the player |
| Violet | Explorer | Rewards new corridors while remaining relevant to the player |

### Special Abilities

Special abilities display a warning before activation:

- Red: temporary overdrive
- Orange: ambush-target lock
- Teal: flanking speed boost
- Violet: temporary cloak

Abilities are disabled while a Sentinel is vulnerable or respawning. A frozen Sentinel cannot damage the player.

### Persistent Q-Learning

The AI uses lightweight tabular Q-learning with no external machine-learning dependency. State encoding includes nearby walls, relative target direction, distance, heading, and behavior mode.

Each personality receives different movement rewards and event rewards. Catching the player is rewarded; being eaten during Overclock is penalized. Trained tables are stored in `ai_memory.json`, loaded at startup, and updated during real play.

Periodic saves are non-blocking: NeoPac copies the compact tables on the game thread, then encodes and writes JSON in a background thread. The final save is safely completed when the game exits.

### Optional Offline Training

```bash
python3 train_ai.py --episodes 500 --steps 80
```

For a larger training run:

```bash
python3 train_ai.py --episodes 5000 --steps 80
```

Large repeated runs eventually provide diminishing returns because the finite state table becomes well explored. Normal gameplay continues training the same brains.

## Procedural Maze Generation

Mazes are generated from deterministic seeds using depth-first carving, added loops, a connected central hub, fixed portal tunnels, and validated spawn locations.

Generation guarantees:

- Every collectible belongs to the reachable maze component
- Player and Sentinel spawns are open
- Portal entrances remain connected
- All six power cores appear exactly once
- The same seed reproduces the same maze
- Daily mode produces a date-based stable seed

Sentinel route maps use a bounded shared LRU cache. Multiple Sentinels targeting the same tile reuse the same BFS distance map instead of scanning the complete maze independently.

## Accessibility

| Preset | Changes |
|---|---|
| Standard | Full effects and original palette |
| Reduced Flash | Reduces flash intensity |
| Colorblind | Uses a colorblind-friendly Sentinel palette |
| Low Motion | Reduces particles and flashes, disables scanlines and screen shake |

Accessibility can be changed from the main menu or pause menu without restarting the game.

## Display and Performance

NeoPac renders to a fixed `672 × 804` logical canvas. The canvas is letterboxed to preserve its aspect ratio at arbitrary window sizes.

Fullscreen first attempts SDL accelerated scaling. If the renderer is unavailable, the game automatically falls back to bounded software scaling. The fallback keeps the game playable rather than aborting startup.

Press `F3` to show:

- Current FPS and total frame time
- Event-processing time
- Game update/draw time
- Presentation/scaling time
- Particle count
- AI state count, mode, difficulty, and maze seed

Frames taking at least 25 ms are written to the diagnostic log with stage-level timings.

## Audio

- `assets/music/neopac_theme.ogg` is a loopable 16-second background track
- Synthesized fallback audio keeps the game functional if the OGG cannot be loaded
- Sound effects cover dots, power cores, dash, deaths, level transitions, and Sentinel ability warnings
- The game remains playable when no audio device is available

## Persistent and Runtime Files

| Path | Purpose | Tracked by Git |
|---|---|---|
| `ai_memory.json` | Bundled and continuously learned Sentinel Q tables | Yes |
| `profile.json` | Local settings, scores, and player statistics | No |
| `logs/` | Runtime diagnostics and per-module logs | No |
| `assets/music/neopac_theme.ogg` | Background music | Yes |

Profile writes and AI-memory writes use temporary files followed by atomic replacement to reduce corruption risk.

## Logs

Logs are size-limited and rotate automatically.

| Log | Contents |
|---|---|
| `logs/neopac.log` | Game lifecycle, slow frames, performance summaries, gameplay events |
| `logs/profile.log` | Profile loading and saving |
| `logs/game_modes.log` | Mode selection and timers |
| `logs/difficulty.log` | Difficulty changes |
| `logs/powerups.log` | Power activation, expiration, and shield use |
| `logs/sentinel_abilities.log` | Sentinel ability warnings and activations |
| `logs/accessibility.log` | Accessibility changes |
| `logs/controls.log` | Keyboard layout and gamepad detection |
| `logs/audio.log` | Music, sound effects, and audio-device failures |
| `logs/menu.log` | Main-menu tab navigation |

The main log is limited to 512 KB with three backups. Feature logs are limited to 256 KB with two backups each.

## Project Structure

```text
neo-pac/
├── main.py                    # Entry point and display initialization
├── game.py                    # Game loop and high-level state machine
├── settings.py                # Global constants and colors
├── maze.py                    # Procedural generation, drawing, collision, route cache
├── player.py                  # Movement, dash, collision, collection
├── enemy.py                   # Sentinel movement, targeting, drawing
├── learning_ai.py             # Persistent tabular Q-learning
├── train_ai.py                # Offline training tool
├── sentinel_abilities.py      # Personality-specific special abilities
├── powerups.py                # Six power definitions and timers
├── game_modes.py              # Independent game-mode rules
├── difficulty.py              # Difficulty presets
├── accessibility.py           # Accessibility presets and palettes
├── controls.py                # Keyboard layouts and gamepad input
├── menu_system.py             # Tab and menu-selection state
├── ui.py                      # HUD, menus, particles, overlays
├── audio_manager.py           # Fault-tolerant audio facade
├── pellets.py                 # Audio synthesis and sound loading
├── profile.py                 # Persistent settings and statistics
├── localization.py            # Turkish and English text
├── diagnostics.py             # Rotating logs and frame monitoring
├── ai_memory.json             # Trained AI memory
├── requirements.txt
├── assets/music/neopac_theme.ogg
└── test_*.py                  # Unit, integration, regression, and performance tests
```

## Tests

Run the complete suite:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m unittest -v
```

The suite currently covers:

- Procedural-maze uniqueness, connectivity, spawns, portals, and power distribution
- Dash-against-wall movement regression
- Sentinel respawn and Overclock vulnerability
- Stationary-player catch behavior across generated mazes
- All powers, modes, difficulties, and accessibility presets
- Keyboard layouts and gamepad events
- Tab navigation, mouse clicks, and power-name rendering
- Profile persistence and localization
- Audio failure safety
- Separate rotating logs
- Shared bounded route caching
- Non-blocking AI saves

## Troubleshooting

### The game opens and immediately closes

Run it from a terminal and inspect `logs/neopac.log`:

```bash
python3 main.py
```

### Fullscreen is slow

Press `F3` and check whether `event`, `game`, or `presentation` time is high. The same stage details are written to `logs/neopac.log`. Try windowed mode or the Low Motion preset if the system has no accelerated SDL renderer.

### No sound

The game intentionally continues without audio. Check `logs/audio.log` for the exact device or mixer error.

### AI memory becomes invalid

The loader falls back safely when JSON cannot be parsed. Keep a copy of `ai_memory.json` before replacing trained tables manually.

## Development Notes

- The project intentionally stays dependency-light: only Pygame is required at runtime.
- Runtime logs and personal profile data are ignored by Git.
- The bundled AI memory is versioned because it is part of the shipped gameplay behavior.
- New gameplay systems should include a focused module, a separate rotating log when stateful, and at least one regression or integration test.

## License

NeoPac is released under the [MIT License](LICENSE). You may use, modify, and
redistribute the project as long as the copyright and license notice are kept.
