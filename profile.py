"""Persistent player profile, settings and lifetime statistics."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from diagnostics import get_feature_logger


PROFILE_FILE = Path(__file__).resolve().parent / "profile.json"

DEFAULT_PROFILE = {
    "version": 1,
    "settings": {
        "mode": "classic",
        "difficulty": "normal",
        "accessibility": "standard",
        "control_layout": "wasd_arrows",
        "language": "tr",
        "muted": False,
        "fullscreen": False,
        "window_size": None,
        "power_labels": True,
    },
    "stats": {
        "high_score": 0,
        "highest_level": 1,
        "games_played": 0,
        "total_score": 0,
        "play_frames": 0,
        "dots_collected": 0,
        "sentinels_eaten": 0,
        "best_combo": 0,
        "daily_best": 0,
    },
    "daily_records": {},
}


class ProfileStore:
    def __init__(self, path=None):
        selected_path = path or os.environ.get("NEOPAC_PROFILE_PATH") or PROFILE_FILE
        self.path = Path(selected_path)
        self.logger = get_feature_logger("profile")
        self.data = self._load()

    def _load(self):
        data = copy.deepcopy(DEFAULT_PROFILE)
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data["settings"].update(raw.get("settings", {}))
                data["stats"].update(raw.get("stats", {}))
                if isinstance(raw.get("daily_records"), dict):
                    data["daily_records"].update(raw["daily_records"])
        except FileNotFoundError:
            self.logger.info("Yeni profil olusturulacak | yol=%s", self.path)
        except (OSError, ValueError, TypeError) as exc:
            self.logger.warning("Profil okunamadi, varsayilan kullanildi | hata=%s", exc)
        return data

    def setting(self, name, default=None):
        return self.data["settings"].get(name, default)

    def set_setting(self, name, value):
        self.data["settings"][name] = value
        self.logger.info("Ayar degisti | %s=%s", name, value)

    def stat(self, name, default=0):
        return self.data["stats"].get(name, default)

    def increment(self, name, amount=1):
        self.data["stats"][name] = self.stat(name) + amount

    def maximum(self, name, value):
        self.data["stats"][name] = max(self.stat(name), value)

    def record_daily(self, day_key, score):
        previous = int(self.data["daily_records"].get(day_key, 0))
        self.data["daily_records"][day_key] = max(previous, int(score))
        self.maximum("daily_best", score)

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(self.path.suffix + ".tmp")
            temp.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp.replace(self.path)
            self.logger.info("Profil kaydedildi | yol=%s", self.path)
            return True
        except OSError as exc:
            self.logger.error("Profil kaydedilemedi | hata=%s", exc)
            return False
