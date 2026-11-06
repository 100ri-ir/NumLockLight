# -*- coding: utf-8 -*-
"""Locate and register bundled assets (fonts / icons / sounds).

Fixes in 1.0.2:
- Registers Vazirmatn with Windows GDI (AddFontResourceExW) and broadcasts
  WM_FONTCHANGE so Tkinter and system controls see the font family.
- Automatically copies Vazirmatn .ttf files into `webui/fonts/` if missing
  so pywebview's internal HTTP server can serve them directly.
- Provides `get_webfont_css()` with embedded Base64 data URIs so WebView2
  is 100% guaranteed to apply Vazirmatn regardless of CORS or file paths.
"""
import base64
import os
import shutil

from .constants import FONTS_DIR, ICONS_DIR, SOUNDS_DIR, WEBUI_DIR

FONT_FILES = {
    "regular": "Vazirmatn-Regular.ttf",
    "medium": "Vazirmatn-Medium.ttf",
    "semibold": "Vazirmatn-SemiBold.ttf",
    "bold": "Vazirmatn-Bold.ttf",
}

FONT_WEIGHTS = {
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
}

_fonts_registered = False
_webfont_css_cache = None


def _ensure_webui_fonts():
    """Ensure webui/fonts/ has copies of Vazirmatn-*.ttf for local serving."""
    webui_fonts = os.path.join(WEBUI_DIR, "fonts")
    try:
        os.makedirs(webui_fonts, exist_ok=True)
        for fn in FONT_FILES.values():
            src = os.path.join(FONTS_DIR, fn)
            dst = os.path.join(webui_fonts, fn)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
    except Exception:
        pass


def register_fonts():
    """Make Vazirmatn available to Windows GDI, Tk, Pillow, and WebView2."""
    global _fonts_registered
    if _fonts_registered:
        return
    _fonts_registered = True

    _ensure_webui_fonts()

    if os.name == "nt":
        import ctypes
        added = 0
        for fn in FONT_FILES.values():
            p = font_path_by_filename(fn)
            if os.path.exists(p):
                try:
                    # 0x10 = FR_PRIVATE — process-local, visible to GDI/Tk
                    # in this process immediately, no system-wide install.
                    res = ctypes.windll.gdi32.AddFontResourceExW(p, 0x10, 0)
                    if res > 0:
                        added += 1
                except Exception:
                    pass
        # 1.1.0: the WM_FONTCHANGE broadcast to every top-level window was
        # removed — it only informs OTHER processes (we register FR_PRIVATE,
        # which is process-local) and SendMessageTimeoutW could block the
        # startup for up to its full timeout on machines with hung windows.


def font_path_by_filename(fn):
    p1 = os.path.join(FONTS_DIR, fn)
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(WEBUI_DIR, "fonts", fn)
    if os.path.exists(p2):
        return p2
    return p1


def font_path(kind="regular"):
    fn = FONT_FILES.get(kind, FONT_FILES["regular"])
    return font_path_by_filename(fn)


def get_webfont_css():
    """Build @font-face CSS with embedded base64 TTFs for guaranteed loading."""
    global _webfont_css_cache
    if _webfont_css_cache is not None:
        return _webfont_css_cache

    rules = []
    for kind, fn in FONT_FILES.items():
        path = font_path_by_filename(fn)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            weight = FONT_WEIGHTS.get(kind, 400)
            rules.append(
                '@font-face {'
                ' font-family: "Vazirmatn";'
                ' src: url("data:font/ttf;base64,%s") format("truetype");'
                ' font-weight: %d;'
                ' font-style: normal;'
                ' font-display: block;'
                '}' % (b64, weight)
            )
        except Exception:
            pass

    _webfont_css_cache = "\n".join(rules)
    return _webfont_css_cache


def icon_path(name):
    return os.path.join(ICONS_DIR, name)


def sound_path(name):
    return os.path.join(SOUNDS_DIR, name)


def sound_exists(name):
    return os.path.exists(sound_path(name))