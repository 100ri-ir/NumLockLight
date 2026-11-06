# -*- coding: utf-8 -*-
"""i18n — English base strings + complete Persian translation.

The program logic and layout are language-agnostic; this module only
provides translated text for the tray, OSD and system dialogs. The web UI
carries its own copy of the same strings (see webui/app.js).
"""

LANG = "fa"  # updated at runtime from settings

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"

_TR = {
    # ------------------------------------------------------------- tray ----
    "tray_settings": {"fa": "تنظیمات", "en": "Settings"},
    "tray_show_osd": {"fa": "پیش‌نمایش اعلان", "en": "Preview notification"},
    "tray_indicator": {"fa": "نشانگر فعال باشد", "en": "Indicator enabled"},
    "tray_startup": {"fa": "اجرای خودکار با ویندوز", "en": "Start with Windows"},
    "tray_about": {"fa": "درباره برنامه", "en": "About"},
    "tray_quit": {"fa": "خروج", "en": "Quit"},
    "tray_toggle_key": {"fa": "تغییر وضعیت {}", "en": "Toggle {}"},
    # -------------------------------------------------------------- OSD ----
    "osd_turned_on": {"fa": "{} روشن شد", "en": "{} is ON"},
    "osd_turned_off": {"fa": "{} خاموش شد", "en": "{} is OFF"},
    "osd_drag_hint": {"fa": "برای جابه‌جایی بکشید — رها کنید تا ذخیره شود",
                      "en": "Drag to move — release to save"},
    # -------------------------------------------------------- dialogs -----
    "already_running": {
        "fa": "برنامه از قبل در حال اجراست.\nآیکون آن در نوار وظیفه (کنار ساعت) قرار دارد.",
        "en": "The program is already running.\nIts icon is in the taskbar (next to the clock)."},
    "already_running_title": {"fa": "برنامه در حال اجراست", "en": "Already running"},
    "webview2_missing": {
        "fa": ("برای نمایش پنجره تنظیمات، «WebView2» ویندوز لازم است و روی سیستم "
               "شما یافت نشد.\n\nهم‌اکنون دانلود و نصب شود؟"),
        "en": ("The settings window needs the Windows \"WebView2\" runtime, which was "
               "not found on this system.\n\nDownload and install it now?")},
    "webview2_missing_title": {"fa": "نیازمندی WebView2", "en": "WebView2 required"},
    "ui_failed": {
        "fa": "نمایش پنجره تنظیمات ممکن نشد.\nبرنامه همچنان در نوار وظیفه فعال است.",
        "en": "Could not open the settings window.\nThe app keeps running in the tray."},
    "ui_failed_title": {"fa": "خطای رابط کاربری", "en": "UI error"},
    "startup_failed": {"fa": "تنظیم اجرای خودکار انجام نشد", "en": "Could not change startup"},
    "startup_error": {"fa": "خطای راه‌اندازی", "en": "Startup error"},
    "windows_only": {
        "fa": "این برنامه مخصوص ویندوز است؛ حالت توسعه اجرا شد.",
        "en": "This program targets Windows; running in development mode."},
    "reset_done": {"fa": "تنظیمات به حالت پیش‌فرض برگشت", "en": "Settings restored to defaults"},
}


def tr(key, lang=None):
    """Translated string for the current (or given) language."""
    lang = lang or LANG
    entry = _TR.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key


def set_language(lang):
    global LANG
    LANG = "en" if str(lang).lower().startswith("en") else "fa"


def key_name(key_id, lang=None):
    """Display name of a key in the current language."""
    from .constants import KEYS
    lang = lang or LANG
    k = KEYS.get(key_id, {})
    return k.get(lang) or k.get("name", key_id)


def fa_digits(text):
    """ASCII digits → Persian digits (only when UI language is Farsi)."""
    if LANG != "fa":
        return str(text)
    table = str.maketrans("0123456789", PERSIAN_DIGITS)
    return str(text).translate(table)


# --------------------------------------------------------------------------
# Complex-text shaping (1.0.1)
# --------------------------------------------------------------------------
# Tk's Windows text engine and Pillow-without-raqm (stock Windows wheels
# ship no libraqm — python-pillow/Pillow#7126) draw codepoints one by one,
# left to right: Persian appears disconnected and mirrored. The fix is to
# pre-shape the string into Arabic presentation forms and apply the
# Unicode bidi algorithm BEFORE handing it to such engines:
#     get_display(arabic_reshaper.reshape(text))
# Verified against the authoritative fribidi/raqm reference (visual ink
# layout matches at IoU 0.965) — see spike/SPIKE-RESULT.md and
# BUILD-REPORT.md. Never call this for text that a native renderer will
# shape itself (MessageBoxW, Shell_NotifyIcon tooltips/balloons, raqm).

_PROBE_PENDING = object()   # sentinel: shaping libs not probed yet
_shape_fn = _PROBE_PENDING  # resolved on first use


def shape(text):
    """Shape + bidi-reorder `text` for dumb LTR renderers (Tk, raw Pillow).

    Latin substrings and digits keep their logical order (base direction
    is auto-detected from the first strong character, exactly like the
    Unicode paragraph-direction rules). Falls back to the raw string if
    the shaping libraries are unavailable (the self-check logs that).
    """
    global _shape_fn
    if not text:
        return text
    if _shape_fn is _PROBE_PENDING:
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            _shape_fn = lambda s: get_display(arabic_reshaper.reshape(s))
        except Exception:
            from . import selfcheck
            selfcheck.log("strings.shape(): arabic-reshaper/python-bidi not "
                          "available; Persian text will render unshaped")
            _shape_fn = None
    if _shape_fn is None:
        return text
    try:
        return _shape_fn(text)
    except Exception:
        return text
