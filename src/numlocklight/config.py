# -*- coding: utf-8 -*-
"""Settings persistence: load / save / migrate / reset (schema v3)."""
import copy
import json
import os
import tempfile
import time

from .constants import (
    CONFIG_FILE_NAME, DEFAULTS, GREEN, KEY_ORDER, RED,
    data_dir as _data_dir,
)

CONFIG_FILE = None
_last_save = 0.0


def _config_path():
    global CONFIG_FILE
    if CONFIG_FILE is None:
        CONFIG_FILE = os.path.join(_data_dir(), CONFIG_FILE_NAME)
    return CONFIG_FILE


def get_data_dir():
    return _data_dir()


def _deep_merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _sanitize(settings):
    """Clamp / repair whatever the stored file contains."""
    settings["schema"] = 3
    lang = settings.get("language", "fa")
    settings["language"] = "en" if str(lang).lower().startswith("en") else "fa"
    settings["theme"] = "light" if settings.get("theme") == "light" else "dark"
    settings["tray"]["mode"] = "single" if settings["tray"].get("mode") == "single" else "per_key"
    if settings["tray"].get("style") not in ("badge", "keycap", "led", "ring", "glow", "icon"):
        settings["tray"]["style"] = "badge"
    if settings["tray"].get("size") not in ("sm", "md", "lg"):
        settings["tray"]["size"] = "md"

    for kid in KEY_ORDER:
        k = settings["keys"].setdefault(kid, copy.deepcopy(DEFAULTS["keys"]["num"]))
        k["enabled"] = bool(k.get("enabled", False))
        k["show_off"] = bool(k.get("show_off", True))
        for field, fallback in (("color_on", GREEN), ("color_off", RED)):
            v = str(k.get(field, fallback)).strip()
            if not v.startswith("#") or len(v) not in (4, 7):
                v = fallback
            k[field] = v

    o = settings["osd"]
    if o.get("position") not in ("top_left", "top_center", "top_right", "middle_left",
                                 "center", "middle_right", "bottom_left", "bottom_center",
                                 "bottom_right", "custom"):
        o["position"] = "bottom_center"
    try:
        o["custom_x"] = min(1.0, max(0.0, float(o.get("custom_x", 0.5))))
        o["custom_y"] = min(1.0, max(0.0, float(o.get("custom_y", 0.92))))
        o["duration_ms"] = min(4000, max(300, int(o.get("duration_ms", 1200))))
        o["scale"] = min(1.6, max(0.8, float(o.get("scale", 1.0))))
    except Exception:
        o.update(copy.deepcopy(DEFAULTS["osd"]))

    try:
        settings["poll_ms"] = min(600, max(80, int(settings.get("poll_ms", 150))))
    except Exception:
        settings["poll_ms"] = 150

    s = settings["sound"]
    if s.get("on_sound") not in ("chime", "glass", "rise", "select", "none"):
        s["on_sound"] = "chime"
    if s.get("off_sound") not in ("fall", "tick", "soft", "none"):
        s["off_sound"] = "tick"
    try:
        s["volume"] = min(100, max(0, int(s.get("volume", 70))))
    except Exception:
        s["volume"] = 70
    return settings


def load():
    settings = copy.deepcopy(DEFAULTS)
    data = _load_json(_config_path())
    if isinstance(data, dict):
        schema = int(data.get("schema", 0) or 0)
        if schema <= 2:
            data = _migrate_v2(data)
        _deep_merge(settings, data)
    return _sanitize(settings)


def _migrate_v2(old):
    """v2 (2.0.x) → v3: unified green/red colors, language, custom OSD pos."""
    if not isinstance(old, dict):
        return {}
    out = copy.deepcopy(old)
    out["language"] = out.get("language", "fa")
    keys = out.get("keys") or {}
    for kid, k in keys.items():
        if isinstance(k, dict):
            # every key now follows the universal green=on / red=off scheme
            k["color_on"] = GREEN
            k["color_off"] = RED
    osd = out.get("osd") or {}
    if isinstance(osd, dict):
        osd.setdefault("custom_x", 0.5)
        osd.setdefault("custom_y", 0.92)
    return out


def save(settings, force=False):
    global _last_save
    now = time.time()
    if not force and now - _last_save < 0.15:
        return False
    _last_save = now
    path = _config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def reset():
    settings = copy.deepcopy(DEFAULTS)
    save(settings, force=True)
    return settings
