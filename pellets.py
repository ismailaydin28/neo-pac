# pellets.py — Procedural sound generation (no external audio files needed)
# Generates all game sounds via pygame.sndarray / numpy-free pure-Python synthesis.

import pygame
import math
import struct
import array as arr
from pathlib import Path


BGM_FILE = Path(__file__).resolve().parent / "assets" / "music" / "neopac_theme.ogg"


def _generate_wave(frequency: float, duration_s: float,
                   wave_type: str = 'sine',
                   sample_rate: int = 44100,
                   volume: float = 0.4,
                   fade_out: bool = True) -> pygame.mixer.Sound:
    """Generate a pygame Sound from a synthesised waveform."""
    n_samples = int(sample_rate * duration_s)
    buf = arr.array('h', [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        fade = 1.0
        if fade_out:
            fade = 1.0 - (i / n_samples)

        if wave_type == 'sine':
            val = math.sin(2 * math.pi * frequency * t)
        elif wave_type == 'square':
            val = 1.0 if math.sin(2 * math.pi * frequency * t) >= 0 else -1.0
        elif wave_type == 'sawtooth':
            val = 2 * ((frequency * t) % 1.0) - 1.0
        elif wave_type == 'triangle':
            val = 2 * abs(2 * ((frequency * t) % 1.0) - 1.0) - 1.0
        else:
            val = math.sin(2 * math.pi * frequency * t)

        buf[i] = int(val * fade * max_amp)

    sound = pygame.sndarray.make_sound(
        pygame.sndarray.array(
            pygame.Surface((1, 1))  # dummy — overridden below
        )
    ) if False else None

    # Use raw bytes approach for compatibility
    raw = buf.tobytes()
    sound = pygame.mixer.Sound(buffer=raw)
    return sound


def _generate_sweep(f_start: float, f_end: float, duration_s: float,
                    wave_type: str = 'sine',
                    sample_rate: int = 44100,
                    volume: float = 0.4) -> pygame.mixer.Sound:
    """Frequency sweep (chirp) sound."""
    n_samples = int(sample_rate * duration_s)
    buf = arr.array('h', [0] * n_samples)
    max_amp = int(32767 * volume)
    for i in range(n_samples):
        t = i / sample_rate
        progress = i / n_samples
        freq = f_start + (f_end - f_start) * progress
        fade = 1.0 - progress * 0.7
        if wave_type == 'square':
            val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        elif wave_type == 'sawtooth':
            val = 2 * ((freq * t) % 1.0) - 1.0
        else:
            val = math.sin(2 * math.pi * freq * t)
        buf[i] = int(val * fade * max_amp)

    raw = buf.tobytes()
    return pygame.mixer.Sound(buffer=raw)


def create_sounds() -> dict:
    """
    Create and return a dict of all game sound effects.
    Falls back gracefully if pygame.mixer is not available.
    """
    sounds = {}
    try:
        # Dot pickup — quick high blip
        sounds['dot']       = _generate_sweep(800, 1200, 0.07, 'sine', volume=0.25)
        # Power pellet — rich low-to-high sweep
        sounds['power']     = _generate_sweep(200, 900, 0.3, 'sawtooth', volume=0.5)
        # Ghost eaten — descending electronic crunch
        sounds['ghost_eat'] = _generate_sweep(1500, 300, 0.2, 'square', volume=0.4)
        # Player death — sad descending sweep
        sounds['death']     = _generate_sweep(600, 100, 0.8, 'sawtooth', volume=0.5)
        # Level complete — ascending arpeggio feel
        sounds['level_up']  = _generate_sweep(400, 1600, 0.5, 'sine', volume=0.5)
        # Dash whoosh
        sounds['dash']      = _generate_sweep(300, 1800, 0.15, 'triangle', volume=0.3)
        sounds['sentinel_alert'] = _generate_sweep(950, 1350, 0.18, 'square', volume=0.22)
    except Exception:
        # If sound fails, return empty placeholders
        sounds = {k: None for k in (
            'dot', 'power', 'ghost_eat', 'death', 'level_up', 'dash',
            'sentinel_alert',
        )}
    return sounds


def create_bgm_channel() -> pygame.mixer.Channel | None:
    """
    Play the packaged OGG theme, falling back to a generated ambient drone.
    Returns the dedicated channel or None on failure.
    """
    try:
        channel = pygame.mixer.Channel(0)
        if BGM_FILE.is_file():
            theme = pygame.mixer.Sound(str(BGM_FILE))
            channel.play(theme, loops=-1)
            channel.set_volume(0.34)
            return channel

        # Installation-safe fallback if the optional asset is missing.
        sample_rate = 44100
        duration = 2.0   # 2-second loop
        n = int(sample_rate * duration)
        buf = arr.array('h', [0] * n)
        base_freq = 55.0   # A1 — dark ambient drone
        for i in range(n):
            t = i / sample_rate
            # Layer three oscillators
            v  = 0.3 * math.sin(2 * math.pi * base_freq * t)
            v += 0.2 * math.sin(2 * math.pi * base_freq * 1.5 * t)        # fifth
            v += 0.1 * math.sin(2 * math.pi * base_freq * 2.0 * t)        # octave
            v += 0.05 * math.sin(2 * math.pi * base_freq * 3.0 * t)       # extra harmonic
            # Slow LFO tremolo
            lfo = 0.7 + 0.3 * math.sin(2 * math.pi * 0.25 * t)
            buf[i] = int(v * lfo * 32767 * 0.35)

        sound = pygame.mixer.Sound(buffer=buf.tobytes())
        channel.play(sound, loops=-1)
        channel.set_volume(0.3)
        return channel
    except Exception:
        return None
