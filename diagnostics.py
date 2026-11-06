"""Rotating diagnostics log and low-overhead frame monitoring for NeoPac."""

from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from settings import PERF_REPORT_SECONDS, SLOW_FRAME_MS


LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "neopac.log"


def configure_logging() -> logging.Logger:
    """Create a bounded UTF-8 log; repeated calls never duplicate handlers."""
    logger = logging.getLogger("neopac")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    LOG_DIR.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=512_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_feature_logger(feature: str) -> logging.Logger:
    """Return a bounded, separate logger for one gameplay module."""
    safe_name = "".join(ch for ch in feature.lower() if ch.isalnum() or ch in "_-")
    logger = logging.getLogger(f"neopac.feature.{safe_name}")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    LOG_DIR.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        LOG_DIR / f"{safe_name}.log",
        maxBytes=256_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


class PerformanceMonitor:
    """Aggregate processing costs and throttle individual slow-frame reports."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.started = time.monotonic()
        self.last_report = self.started
        self.last_slow_log = 0.0
        self.frames = 0
        self.slow_frames = 0
        self.total_processing_ms = 0.0
        self.peak_processing_ms = 0.0
        self.total_event_ms = 0.0
        self.total_game_ms = 0.0
        self.total_present_ms = 0.0
        self.peak_event_ms = 0.0
        self.peak_game_ms = 0.0
        self.peak_present_ms = 0.0

    def record(self, processing_ms, frame_ms, state, power, particles, ai_states,
               event_ms=0.0, game_ms=0.0, present_ms=0.0):
        now = time.monotonic()
        self.frames += 1
        self.total_processing_ms += processing_ms
        self.peak_processing_ms = max(self.peak_processing_ms, processing_ms)
        self.total_event_ms += event_ms
        self.total_game_ms += game_ms
        self.total_present_ms += present_ms
        self.peak_event_ms = max(self.peak_event_ms, event_ms)
        self.peak_game_ms = max(self.peak_game_ms, game_ms)
        self.peak_present_ms = max(self.peak_present_ms, present_ms)

        if processing_ms >= SLOW_FRAME_MS:
            self.slow_frames += 1
            if now - self.last_slow_log >= 2.0:
                self.logger.warning(
                    "Yavas kare | islem=%.1fms toplam=%.1fms durum=%s "
                    "guc=%s parcacik=%d ai_durum=%d olay=%.1fms "
                    "oyun=%.1fms sunum=%.1fms",
                    processing_ms, frame_ms, state, power, particles, ai_states,
                    event_ms, game_ms, present_ms,
                )
                self.last_slow_log = now

        if now - self.last_report >= PERF_REPORT_SECONDS:
            average = self.total_processing_ms / max(1, self.frames)
            avg_event = self.total_event_ms / max(1, self.frames)
            avg_game = self.total_game_ms / max(1, self.frames)
            avg_present = self.total_present_ms / max(1, self.frames)
            self.logger.info(
                "Performans | ort_islem=%.2fms tepe=%.1fms yavas=%d/%d "
                "durum=%s guc=%s parcacik=%d ai_durum=%d "
                "ort_olay=%.2fms ort_oyun=%.2fms ort_sunum=%.2fms "
                "tepe_olay=%.1fms tepe_oyun=%.1fms tepe_sunum=%.1fms",
                average, self.peak_processing_ms, self.slow_frames, self.frames,
                state, power, particles, ai_states,
                avg_event, avg_game, avg_present,
                self.peak_event_ms, self.peak_game_ms, self.peak_present_ms,
            )
            self.frames = 0
            self.slow_frames = 0
            self.total_processing_ms = 0.0
            self.peak_processing_ms = 0.0
            self.total_event_ms = 0.0
            self.total_game_ms = 0.0
            self.total_present_ms = 0.0
            self.peak_event_ms = 0.0
            self.peak_game_ms = 0.0
            self.peak_present_ms = 0.0
            self.last_report = now
