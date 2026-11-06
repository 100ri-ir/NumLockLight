# -*- coding: utf-8 -*-
"""Constants, paths and default settings — NumLock Light 1.0.3."""
import os
import sys

from . import __version__

APP_NAME = "NumLock Light"
APP_ID = "NumLockLight100ri"
APP_NAME_FA = "نام‌لاک لایت"
APP_VERSION = __version__
AUTHOR = "sadri1993"
WEBSITE = "https://100ri.ir"
GITHUB_REPO = "https://github.com/100ri-ir/NumLockLight"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

IS_WINDOWS = os.name == "nt"
IS_FROZEN = getattr(sys, "frozen", False)

# --------------------------------------------------------------------------
# Toggle keys registry
# --------------------------------------------------------------------------
# vk: virtual key code | badge: tray letter | keycap: short keycap text
KEYS = {
    "num": {
        "vk": 0x90, "badge": "N", "keycap": "Num", "ext": False,
        "name": "Num Lock", "fa": "نام لاک", "en": "Num Lock",
        "hint_fa": "قفل صفحه اعداد سمت راست کیبورد",
        "hint_en": "Numeric keypad on the right side of the keyboard",
    },
    "caps": {
        "vk": 0x14, "badge": "C", "keycap": "Caps", "ext": False,
        "name": "Caps Lock", "fa": "کپس لاک", "en": "Caps Lock",
        "hint_fa": "قفل حروف بزرگ انگلیسی",
        "hint_en": "Uppercase letters lock",
    },
    "scroll": {
        "vk": 0x91, "badge": "S", "keycap": "ScrLk", "ext": False,
        "name": "Scroll Lock", "fa": "اسکرول لاک", "en": "Scroll Lock",
        "hint_fa": "قفل اسکرول (در بعضی کیبوردها)",
        "hint_en": "Scroll lock (present on some keyboards)",
    },
    "insert": {
        "vk": 0x2D, "badge": "I", "keycap": "Ins", "ext": True,
        "name": "Insert", "fa": "اینسرت", "en": "Insert",
        "hint_fa": "حالت درج/بازنویسی هنگام تایپ",
        "hint_en": "Insert / overwrite typing mode",
    },
}
KEY_ORDER = ("num", "caps", "scroll", "insert")

GREEN = "#22c55e"   # ON  — universal "enabled" color
RED = "#ef4444"     # OFF — universal "disabled" color

# --------------------------------------------------------------------------
# Asset / config paths
# --------------------------------------------------------------------------


def is_portable():
    """Portable = a marker file sits next to the frozen exe (or dev tree)."""
    if IS_FROZEN:
        return os.path.exists(os.path.join(os.path.dirname(sys.executable), "portable.flag"))
    if os.environ.get("NUMLOCKLIGHT_MODE", "").lower() == "installed":
        return False
    return True  # running from source / portable tree


def program_dir():
    if IS_FROZEN:
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_dir():
    if IS_FROZEN:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return meipass
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def data_dir():
    if is_portable():
        base = program_dir()
    else:
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NumLockLight")
    return os.path.join(base, "NumLockLight_Data")


CONFIG_FILE_NAME = "settings.json"
OLD_APPDATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "NumLockLight100ri")

ASSETS_DIR = os.path.join(resource_dir(), "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
WEBUI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webui")

# --------------------------------------------------------------------------
# Choices offered in the settings UI
# --------------------------------------------------------------------------

LANGUAGES = {"fa": "فارسی", "en": "English"}

ICON_STYLES = {
    "badge":  {"fa": "نشان حرفی", "en": "Letter badge",
               "desc_fa": "حرف کلید روی زمینه رنگی (پیشنهادی)",
               "desc_en": "Key letter on a colored tile (recommended)"},
    "keycap": {"fa": "کلید کیبورد", "en": "Keycap",
               "desc_fa": "شکل واقعی کلید با حروف",
               "desc_en": "Realistic 3D keyboard key"},
    "led":    {"fa": "کلاسیک (LED)", "en": "Classic LED",
               "desc_fa": "نقطه نورانی درخشان",
               "desc_en": "Glowing light dot"},
    "ring":   {"fa": "حلقه", "en": "Ring",
               "desc_fa": "حلقه مینیمال و ظریف",
               "desc_en": "Minimal outline ring"},
    "glow":   {"fa": "مهتابی", "en": "Orb",
               "desc_fa": "گوی نورانی با هاله نرم",
               "desc_en": "Soft luminous orb"},
    "icon":   {"fa": "آیکون کیبورد", "en": "Keyboard icon",
               "desc_fa": "آیکون کیبورد با نقطه وضعیت",
               "desc_en": "Keyboard glyph with status dot"},
}
ICON_SIZES = {"sm": 48, "md": 64, "lg": 80}
ICON_SIZES_FA = {"sm": "کوچک", "md": "متوسط", "lg": "بزرگ"}
ICON_SIZES_EN = {"sm": "Small", "md": "Medium", "lg": "Large"}

OSD_POSITIONS = {
    "top_left":     {"fa": "بالا چپ", "en": "Top left"},
    "top_center":   {"fa": "بالا وسط", "en": "Top center"},
    "top_right":    {"fa": "بالا راست", "en": "Top right"},
    "middle_left":  {"fa": "وسط چپ", "en": "Middle left"},
    "center":       {"fa": "وسط صفحه", "en": "Center"},
    "middle_right": {"fa": "وسط راست", "en": "Middle right"},
    "bottom_left":  {"fa": "پایین چپ", "en": "Bottom left"},
    "bottom_center":{"fa": "پایین وسط", "en": "Bottom center"},
    "bottom_right": {"fa": "پایین راست", "en": "Bottom right"},
    "custom":       {"fa": "محل دلخواه (با کشیدن)", "en": "Custom (drag to place)"},
}

SOUND_OPTIONS_ON = {
    "chime": "چایم تأیید",
    "glass": "زنگ شیشه‌ای",
    "rise": "ملایم صعودی",
    "select": "انتخاب",
    "none": "بدون صدا",
}
SOUND_OPTIONS_OFF = {
    "fall": "ملایم نزولی",
    "tick": "تیک کوتاه",
    "soft": "نرم شیشه‌ای",
    "none": "بدون صدا",
}

# --------------------------------------------------------------------------
# Default settings (schema v3 — v1.0.0)
# --------------------------------------------------------------------------
DEFAULTS = {
    "schema": 3,
    "language": "fa",            # fa | en  (UI language)
    "enabled": True,
    "startup": False,
    "balloon": False,
    "poll_ms": 150,
    "theme": "dark",
    "keys": {
        "num":    {"enabled": True,  "color_on": GREEN, "color_off": RED, "show_off": True},
        "caps":   {"enabled": True,  "color_on": GREEN, "color_off": RED, "show_off": True},
        "scroll": {"enabled": False, "color_on": GREEN, "color_off": RED, "show_off": True},
        "insert": {"enabled": False, "color_on": GREEN, "color_off": RED, "show_off": True},
    },
    "tray": {
        "mode": "per_key",        # per_key | single
        "style": "badge",         # badge | keycap | led | ring | glow | icon
        "size": "md",
        "state_text": True,
    },
    "osd": {
        "enabled": True,
        "position": "bottom_center",
        "custom_x": 0.5,          # fractions of the monitor work area (custom mode)
        "custom_y": 0.92,
        "duration_ms": 1200,
        "scale": 1.0,
    },
    "sound": {
        "enabled": False,
        "on_sound": "chime",
        "off_sound": "tick",
        "volume": 70,
        "ui_click": False,
    },
}
