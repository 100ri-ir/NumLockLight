# -*- coding: utf-8 -*-
"""pywebview JS-API bridge — every call from the settings UI lands here.

All paths/values coming from JavaScript are validated against a strict
whitelist before touching the settings object.

1.0.3 fix: the App reference is stored as ``self._app`` (underscore!).
pywebview's js_api discovery (`webview.util.get_functions`) walks every
PUBLIC attribute of the api object and recurses into non-callable objects
that have a ``__module__`` — with a public ``self._app`` it enumerated the
whole App object graph (Tray/Monitor/OSD/the live Tk root), leaking
internal methods to JavaScript, triggering thread-unsafe attribute access
on the Tk root from a foreign thread, and slowing the API injection so
much that the settings UI could boot before the bridge existed (dead
window). Underscore attributes are skipped by that discovery.
"""
from . import config, icons, sound, strings, winapi
from .constants import (
    APP_VERSION, AUTHOR, GITHUB_REPO, ICON_STYLES, KEYS, KEY_ORDER,
    OSD_POSITIONS, SOUND_OPTIONS_OFF, SOUND_OPTIONS_ON, WEBSITE,
)

_ALLOWED_URLS = (WEBSITE, GITHUB_REPO, winapi.WEBVIEW2_DOWNLOAD)

_BOOL_PATHS = {
    "enabled", "balloon", "tray.state_text",
    "osd.enabled", "sound.enabled", "sound.ui_click",
} | {"keys.%s.%s" % (kid, f) for kid in KEYS for f in ("enabled", "show_off")}

_INT_PATHS = {
    "poll_ms": (80, 600),
    "osd.duration_ms": (300, 4000),
    "sound.volume": (0, 100),
}

_FLOAT_PATHS = {
    "osd.scale": (0.8, 1.6),
    "osd.custom_x": (0.0, 1.0),
    "osd.custom_y": (0.0, 1.0),
}

_ENUM_PATHS = {
    "theme": ("dark", "light"),
    "tray.mode": ("per_key", "single"),
    "tray.style": tuple(ICON_STYLES.keys()),
    "tray.size": ("sm", "md", "lg"),
    "osd.position": tuple(OSD_POSITIONS.keys()),
    "sound.on_sound": tuple(SOUND_OPTIONS_ON.keys()),
    "sound.off_sound": tuple(SOUND_OPTIONS_OFF.keys()),
}

_COLOR_RE = __import__("re").compile(r"^#[0-9a-fA-F]{6}$")


def _set(obj, dotted, value):
    parts = dotted.split(".")
    cur = obj
    for part in parts[:-1]:
        cur = cur[part]
    cur[parts[-1]] = value


class Bridge:
    def __init__(self, app):
        self._app = app

    # ------------------------------------------------------------ info --

    def get_manifest(self):
        lang = strings.LANG
        keys = {}
        for kid in KEY_ORDER:
            meta = KEYS[kid]
            keys[kid] = {
                "keycap": meta["keycap"],
                "badge": meta["badge"],
                "name": meta[lang],
                "hint": meta["hint_" + lang],
            }
        styles = {
            sid: {
                "fa": m["fa"],
                "en": m["en"],
                "desc": m["desc_" + lang],
            }
            for sid, m in ICON_STYLES.items()
        }
        return {
            "version": APP_VERSION,
            "author": AUTHOR,
            "website": WEBSITE,
            "github": GITHUB_REPO,
            "system": winapi.windows_version_text(),
            "keys": keys,
            "styles": styles,
            "sounds_on": list(SOUND_OPTIONS_ON.keys()),
            "sounds_off": list(SOUND_OPTIONS_OFF.keys()),
            "webview2": winapi.has_webview2(),
            # NOTE: font_css (≈2.7 MB of base64 TTFs) removed in 1.0.3 —
            # it was shipped through TWO evaluate_js round-trips on every
            # window open, slowing the bridge handshake drastically.
            # The web UI loads Vazirmatn via its own CSS @font-face rules
            # (webui/fonts/*.ttf + local() fallbacks) which is enough.
            "font_css": "",
        }

    def get_settings(self):
        return self._app.settings

    def get_states(self):
        return self._app.get_states()

    def get_startup(self):
        return bool(
            winapi.get_startup()
            if winapi.IS_WINDOWS
            else self._app.settings.get("startup")
        )

    # ---------------------------------------------------------- changes --

    def set_setting(self, path, value):
        try:
            if path in _BOOL_PATHS:
                _set(self._app.settings, path, bool(value))
            elif path in _INT_PATHS:
                lo, hi = _INT_PATHS[path]
                _set(self._app.settings, path, int(min(hi, max(lo, int(float(value))))))
            elif path in _FLOAT_PATHS:
                lo, hi = _FLOAT_PATHS[path]
                v = float(value)
                _set(self._app.settings, path, float(min(hi, max(lo, v))))
            elif path in _ENUM_PATHS:
                if value not in _ENUM_PATHS[path]:
                    return {"ok": False, "error": "invalid value"}
                _set(self._app.settings, path, value)
            elif path.startswith("keys.") and path.endswith(
                (".color_on", ".color_off")
            ):
                v = str(value).strip()
                if not _COLOR_RE.match(v):
                    return {"ok": False, "error": "invalid color"}
                _set(self._app.settings, path, v)
            else:
                return {"ok": False, "error": "unknown path"}
        except Exception as e:
            self._app.on_settings_saved(False, str(e))
            return {"ok": False, "error": str(e)}

        saved = config.save(self._app.settings, force=True)
        self._app.on_settings_changed()
        if saved:
            self._app.on_settings_saved(True, path)
            return {"ok": True}
        return {"ok": False, "error": "save failed"}

    def set_language(self, lang):
        lang = "en" if str(lang).lower().startswith("en") else "fa"
        self._app.settings["language"] = lang
        strings.set_language(lang)
        saved = config.save(self._app.settings, force=True)
        self._app.on_settings_changed()
        if saved:
            self._app.on_settings_saved(True, "language")
        return {"ok": bool(saved)}

    def set_startup(self, enabled):
        enabled = bool(enabled)
        self._app.settings["startup"] = enabled
        ok, err = (True, "")
        if winapi.IS_WINDOWS:
            ok, err = winapi.set_startup(enabled)
        if ok:
            saved = config.save(self._app.settings, force=True)
            self._app.on_settings_changed()
            self._app.on_settings_saved(True, "startup")
            return {"ok": bool(saved), "error": "" if saved else "save failed"}
        self._app.on_settings_saved(False, err)
        return {"ok": False, "error": err}

    def toggle_key(self, kid):
        if kid in KEYS:
            self._app.toggle_key(kid)
        return self._app.get_states()

    def reset_settings(self):
        fresh = config.reset()
        self._app.apply_settings(fresh)
        self._app.on_settings_saved(True, "reset")
        return fresh

    def save_now(self):
        saved = config.save(self._app.settings, force=True)
        self._app.on_settings_changed()
        return {"ok": bool(saved)}

    # ---------------------------------------------------------- sounds --

    def play_sound(self, name, volume=None):
        vol = (
            self._app.settings["sound"]["volume"]
            if volume is None
            else int(float(volume))
        )
        sound.play(str(name), vol)
        return {"ok": True}

    def ui_click(self):
        if self._app.settings["sound"].get("ui_click"):
            sound.play("click", self._app.settings["sound"]["volume"])
        return {"ok": True}

    # ------------------------------------------------------------ icons --

    def get_icon_previews(self):
        color = self._app.settings["keys"]["num"]["color_on"]
        return {
            sid: icons.style_preview("num", sid, 72, True, color)
            for sid in ICON_STYLES
        }

    def get_tray_preview(self, style=None, size_name=None):
        s = self._app.settings
        style = style or s["tray"]["style"]
        size_name = size_name or s["tray"]["size"]
        states = self._app.get_states()
        out = []
        if s["tray"]["mode"] == "single":
            img = icons.combined_tray_image(
                states,
                {
                    **s,
                    "tray": {**s["tray"], "style": style, "size": size_name},
                },
            )
            out.append(icons.png_dataurl(img))
        else:
            for kid in KEY_ORDER:
                k = s["keys"][kid]
                if not k["enabled"]:
                    continue
                if not states.get(kid) and not k.get("show_off", True):
                    continue
                img = icons.tray_image(
                    kid, states.get(kid, False), k, style, size_name
                )
                out.append(icons.png_dataurl(img))
        return out

    # -------------------------------------------------------------- OSD --

    def osd_preview(self):
        s = self._app.settings
        kid = "num" if s["keys"]["num"]["enabled"] else "caps"
        self._app.post(lambda: self._app.show_osd_preview(kid))
        return {"ok": True}

    def osd_arrange(self):
        self._app.start_osd_arrange()
        return {"ok": True}

    # -------------------------------------------------------------- misc --

    def open_url(self, url):
        url = str(url)
        if any(url == u or url.startswith(u + "/") for u in _ALLOWED_URLS):
            winapi.open_url(url)
            return {"ok": True}
        return {"ok": False, "error": "not allowed"}

    def minimize_window(self):
        self._app.minimize_settings_window()
        return {"ok": True}

    def close_window(self):
        config.save(self._app.settings, force=True)
        self._app.close_settings_window()
        return {"ok": True}

    def quit_app(self):
        self._app.quit()
        return {"ok": True}