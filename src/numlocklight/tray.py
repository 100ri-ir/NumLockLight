# -*- coding: utf-8 -*-
"""System-tray management (pystray) — per-key icons or one combined icon.

Fixes in 1.0.3:
1. Per-icon resilient construction: previously ANY exception while building
   ONE pystray.Icon (font hiccup, PIL error, ...) aborted the whole tray —
   silently, leaving the app with no tray icon and no control surface.
   Each icon is now built and launched independently; a failure only
   disables that icon and is logged.
2. refresh() only re-assigns icon/title when the rendered content actually
   changed (per-icon signature cache). pystray's icon setter destroys and
   reloads the HICON and calls Shell_NotifyIcon(NIM_MODIFY) every time —
   re-assigning identical images right after startup raced the setup
   thread's NIM_ADD (briefly destroying the handle the shell was showing)
   and caused needless DestroyIcon/LoadImage churn on every key event.
3. `healthy` flag tells the app whether ANY tray icon exists, so it can
   open the settings window as a fallback control surface when the tray
   is completely unavailable.
"""
import queue
import threading
import time

from . import icons, selfcheck, strings, winapi
from .constants import APP_NAME, IS_WINDOWS, KEY_ORDER

try:
    import pystray
    _PYSTRAY = True
except Exception as _e:
    pystray = None
    _PYSTRAY = False
    selfcheck.log("tray: pystray import failed: %r" % (_e,))


class Tray:
    def __init__(self, app):
        self.app = app
        self._icons = {}
        self._combined = None
        self._running = True
        self._writer = None
        self._wake = threading.Event()
        self._ready = {}
        self._notify_q = queue.Queue()
        self._menu_sig = None
        self._started_at = None
        self._first_show_done = False
        self._img_sig = {}          # kid -> last applied (style, size, on, color) signature
        self._combined_sig = None   # same for the combined icon
        self.healthy = False        # True when at least one icon object exists

    # ---------------------------------------------------------------- API --

    def start(self):
        self._started_at = time.perf_counter()
        if not IS_WINDOWS:
            selfcheck.log("tray: not Windows — tray disabled (dev mode)")
            return
        if not _PYSTRAY:
            selfcheck.log(
                "tray: pystray missing — NO tray icon will be created"
            )
            return

        states = self.app.get_states()
        s = self.app.settings

        menu = None
        try:
            menu = self._build_menu()
            self._menu_sig = self._menu_signature()
        except Exception as e:
            selfcheck.log("tray: menu build failed — icons get no menu", e)

        # -- per-key icons: each one independent (1.0.3) -----------------
        for kid in KEY_ORDER:
            try:
                k = s["keys"][kid]
                self._ready[kid] = threading.Event()
                self._icons[kid] = pystray.Icon(
                    "NumLockLight_" + kid,
                    icons.tray_image(
                        kid,
                        states.get(kid, False),
                        k,
                        s["tray"]["style"],
                        s["tray"]["size"],
                    ),
                    self._key_tooltip(kid, states.get(kid, False)),
                    menu,
                )
                self._img_sig[kid] = (
                    s["tray"]["style"], s["tray"]["size"],
                    states.get(kid, False), k.get("color_on"), k.get("color_off"),
                )
            except Exception as e:
                selfcheck.log("tray: construction failed for '%s'" % kid, e)
                self._ready.pop(kid, None)
                self._icons.pop(kid, None)

        # -- combined icon --------------------------------------------------
        try:
            self._ready["__combined__"] = threading.Event()
            self._combined = pystray.Icon(
                "NumLockLightCombined",
                icons.combined_tray_image(states, s),
                self._combined_tooltip(states),
                menu,
            )
        except Exception as e:
            selfcheck.log("tray: construction failed for combined icon", e)
            self._ready.pop("__combined__", None)
            self._combined = None

        if not self._icons and self._combined is None:
            selfcheck.log(
                "tray: NO icon could be constructed — tray unavailable"
            )
            return

        self.healthy = True

        for key, icon in list(self._icons.items()) + [
            ("__combined__", self._combined)
        ]:
            try:
                self._launch_icon(key, icon)
                selfcheck.log("tray: icon '%s' thread started" % key)
            except Exception as e:
                selfcheck.log("tray: launch failed for '%s'" % key, e)

        self._writer = threading.Thread(
            target=self._loop, name="tray-writer", daemon=True
        )
        self._writer.start()

    def _should_icon_be_visible(self, key):
        s = self.app.settings
        if not s.get("enabled", True):
            return False
        show_combined = s["tray"].get("mode") == "single"
        if key == "__combined__":
            return bool(show_combined)
        if show_combined:
            return False
        k = s["keys"].get(key, {})
        if not k.get("enabled", False):
            return False
        on = self.app.get_states().get(key, False)
        return bool(on or k.get("show_off", True))

    def _launch_icon(self, key, icon):
        """Launch a single pystray icon in its own daemon thread."""
        ev = self._ready[key]

        def _setup(ic):
            try:
                ic.visible = self._should_icon_be_visible(key)
            except Exception as e:
                selfcheck.log(
                    "tray: setup visible failed for '%s'" % (key,), e
                )
            finally:
                ev.set()

        def _run():
            try:
                icon.run(setup=_setup)
            except Exception as e:
                selfcheck.log("tray: icon.run failed for '%s'" % (key,), e)
                ev.set()

        t = threading.Thread(target=_run, name="tray-icon-" + key, daemon=True)
        t.start()

    def stop(self):
        self._running = False
        self._wake.set()
        if self._writer is not None:
            self._writer.join(timeout=1.5)
        for icon in list(self._icons.values()) + [self._combined]:
            if icon is None:
                continue
            try:
                icon.visible = False
                icon.stop()
            except Exception as e:
                selfcheck.log("tray: stop error", e)
        selfcheck.log("tray: stopped")

    def request_refresh(self):
        self._wake.set()

    def refresh(self):
        if not self._icons and not self._combined:
            return
        s = self.app.settings
        states = self.app.get_states()
        show_combined = s["tray"]["mode"] == "single"
        menu = None
        sig = self._menu_signature()
        if sig != self._menu_sig:
            self._menu_sig = sig
            menu = self._build_menu()

        for kid, icon in self._icons.items():
            if icon is None:
                continue
            k = s["keys"][kid]
            on = states.get(kid, False)
            visible = bool(
                s["enabled"]
                and k["enabled"]
                and not show_combined
                and (on or k.get("show_off", True))
            )
            try:
                # only touch the HICON when the rendered content really
                # changed — pystray destroy/reloads the icon on EVERY
                # assignment (see module docstring, fix 1.0.3/2)
                img_sig = (
                    s["tray"]["style"], s["tray"]["size"], on,
                    k.get("color_on"), k.get("color_off"),
                )
                if self._img_sig.get(kid) != img_sig:
                    self._img_sig[kid] = img_sig
                    icon.icon = icons.tray_image(
                        kid, on, k, s["tray"]["style"], s["tray"]["size"]
                    )
                    icon.title = self._key_tooltip(kid, on)
                if menu is not None:
                    icon.menu = menu
                if icon.visible != visible:
                    icon.visible = visible
            except Exception as e:
                selfcheck.log("tray: refresh failed for '%s'" % kid, e)

        if self._combined is not None:
            try:
                vis_comb = bool(s["enabled"] and show_combined)
                comb_sig = (
                    s["tray"]["style"], s["tray"]["size"], show_combined,
                    tuple(sorted(states.items())),
                    tuple(
                        (kid, k.get("enabled"), k.get("color_on"), k.get("color_off"))
                        for kid, k in s["keys"].items()
                    ),
                )
                if self._combined_sig != comb_sig:
                    self._combined_sig = comb_sig
                    self._combined.icon = icons.combined_tray_image(states, s)
                    self._combined.title = self._combined_tooltip(states)
                if menu is not None:
                    self._combined.menu = menu
                if self._combined.visible != vis_comb:
                    self._combined.visible = vis_comb
            except Exception as e:
                selfcheck.log("tray: refresh failed for combined icon", e)

        if not self._first_show_done:
            self._first_show_done = True
            selfcheck.log(
                "tray: first refresh applied %.0f ms after start"
                % ((time.perf_counter() - self._started_at) * 1000,)
            )

    def notify(self, title, message):
        self._notify_q.put((title, message))
        self._wake.set()

    # ------------------------------------------------------------ internals

    def _key_tooltip(self, kid, on):
        name = strings.key_name(kid)
        return "%s — %s" % (name, strings.tr("on" if on else "off"))

    def _combined_tooltip(self, states):
        s = self.app.settings
        parts = []
        for kid in KEY_ORDER:
            if s["keys"][kid]["enabled"] and s["tray"]["state_text"]:
                parts.append(
                    "%s: %s"
                    % (
                        strings.key_name(kid),
                        strings.tr("on" if states.get(kid) else "off"),
                    )
                )
        return "  |  ".join(parts) if parts else APP_NAME

    def _menu_signature(self):
        s = self.app.settings
        return (
            strings.LANG,
            s["tray"]["mode"],
            tuple((kid, s["keys"][kid]["enabled"]) for kid in KEY_ORDER),
        )

    # ------------------------------------------------------ closure helpers
    # pystray inspects `__code__.co_argcount`:
    # - `action` must take at most 2 positional args: `(icon, item)`
    # - `checked` must take EXACTLY 1 positional arg: `(item,)`

    def _make_toggle_action(self, kid):
        def _action(icon, item):
            self.app.toggle_key(kid)
        return _action

    def _make_checked_getter(self, kid):
        def _checked(item):
            return bool(self.app.get_states().get(kid, False))
        return _checked

    def _is_enabled_checked(self, item):
        return bool(self.app.settings.get("enabled", True))

    def _is_startup_checked(self, item):
        return bool(
            winapi.get_startup()
            if IS_WINDOWS
            else self.app.settings.get("startup", False)
        )

    def _build_menu(self):
        if not _PYSTRAY:
            return None
        s = self.app.settings
        items = []

        for kid in KEY_ORDER:
            if not s["keys"][kid]["enabled"]:
                continue
            items.append(
                pystray.MenuItem(
                    strings.tr("tray_toggle_key").format(strings.key_name(kid)),
                    self._make_toggle_action(kid),
                    checked=self._make_checked_getter(kid),
                )
            )
        if items:
            items.append(pystray.Menu.SEPARATOR)

        items += [
            pystray.MenuItem(
                strings.tr("tray_settings"), self._open_settings, default=True
            ),
            pystray.MenuItem(strings.tr("tray_show_osd"), self._preview_osd),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                strings.tr("tray_indicator"),
                self._toggle_enabled,
                checked=self._is_enabled_checked,
            ),
            pystray.MenuItem(
                strings.tr("tray_startup"),
                self._toggle_startup,
                checked=self._is_startup_checked,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(strings.tr("tray_about"), self._open_settings),
            pystray.MenuItem(strings.tr("tray_quit"), self._quit),
        ]
        return pystray.Menu(*items)

    # ------------------------------------------------------ menu callbacks

    def _open_settings(self, icon=None, item=None):
        self.app.open_settings_async()

    def _preview_osd(self, icon=None, item=None):
        self.app.preview_osd_from_tray()

    def _toggle_enabled(self, icon=None, item=None):
        s = self.app.settings
        s["enabled"] = not s["enabled"]
        from . import config
        config.save(s, force=True)
        self.app.on_settings_changed()
        self.request_refresh()

    def _toggle_startup(self, icon=None, item=None):
        s = self.app.settings
        v = not bool(winapi.get_startup() if IS_WINDOWS else s["startup"])
        s["startup"] = v
        if IS_WINDOWS:
            winapi.set_startup(v)
        from . import config
        config.save(s, force=True)
        self.app.on_settings_changed()
        self.request_refresh()

    def _quit(self, icon=None, item=None):
        self.app.quit()

    # ----------------------------------------------------------- the writer

    def _loop(self):
        deadline = time.perf_counter() + 10.0
        for key, ev in self._ready.items():
            ev.wait(max(0.0, deadline - time.perf_counter()))
        for key, ev in self._ready.items():
            if not ev.is_set():
                selfcheck.log("tray: icon '%s' window not ready in time" % key)

        last_fp = None
        while self._running:
            try:
                self._drain_notify()
                s = self.app.settings
                fp = (
                    s["enabled"],
                    s["tray"]["mode"],
                    s["tray"]["style"],
                    s["tray"]["size"],
                    strings.LANG,
                    tuple(
                        (
                            kid,
                            k["enabled"],
                            k["show_off"],
                            k["color_on"],
                            k["color_off"],
                        )
                        for kid, k in s["keys"].items()
                    ),
                    tuple(sorted(self.app.get_states().items())),
                    winapi.get_startup() if IS_WINDOWS else s["startup"],
                )
                if fp != last_fp:
                    last_fp = fp
                    self.refresh()
            except Exception as e:
                selfcheck.log("tray: writer loop error", e)
            self._wake.wait(0.35)
            self._wake.clear()

    def _drain_notify(self):
        while True:
            try:
                title, message = self._notify_q.get_nowait()
            except queue.Empty:
                return
            icon = self._notify_icon()
            if icon is None:
                continue
            try:
                icon.notify(message, title)
            except Exception as e:
                selfcheck.log("tray: notification failed", e)

    def _notify_icon(self):
        s = self.app.settings
        if s["tray"]["mode"] == "single":
            return self._combined
        for kid in KEY_ORDER:
            ic = self._icons.get(kid)
            if ic is not None and s["keys"][kid]["enabled"]:
                return ic
        return self._combined or self._icons.get("num")