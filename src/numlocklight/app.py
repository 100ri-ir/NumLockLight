# -*- coding: utf-8 -*-
"""NumLock Light 1.1.0 — application orchestration.

Architecture:
- Tkinter (OSD window + task pump) runs in its own dedicated daemon thread
  where the Tcl/Tk interpreter is created and owned exclusively. Since 1.1.0
  that thread — and the tkinter import itself — is started LAZILY on the
  first OSD request, so nothing GUI-heavy sits on the startup critical path.
- MainThread is kept free for pywebview (WinForms / EdgeChromium WebView2),
  which strictly requires running on 'MainThread' (STA).
- pystray runs each tray icon message pump in its own daemon thread.
This completely eliminates deadlocks between Tkinter's timer loop and
pywebview's blocking Application.Run() loop.

1.0.3 fix: when the tray ends up with NO icon at all (pystray failure,
missing backend, ...), the settings window now opens automatically at
startup so the user always has a control surface (enable/quit) instead
of an invisible, uncontrollable background process.

1.1.0 STARTUP SPEED fix: the tray icons are now created BEFORE anything
else (monitor + tray start immediately; Tk/OSD is lazy). The self-check
runs in a background thread after the app is up, and pywebview is
pre-warmed in the background so the first "Settings" click still opens
quickly. Previously the self-check imported webview (pulling bottle/ssl
and more) on the startup critical path, adding seconds before the tray
appeared on every launch.
"""
import json
import os
import queue
import sys
import threading
import time

from . import assets, config, selfcheck, sound, strings, winapi
from .constants import (
    APP_NAME, APP_VERSION, IS_WINDOWS, WEBUI_DIR,
)
from .monitor import Monitor
from .strings import tr
from .tray import Tray


class App:
    def __init__(self, dev=False, open_settings=False):
        self.dev = dev
        self.settings = config.load()
        strings.set_language(self.settings.get("language", "fa"))

        # Register fonts before any UI toolkit initializes
        try:
            assets.register_fonts()
        except Exception as e:
            selfcheck.log("assets.register_fonts error", e)

        self._running = True
        self._tasks = queue.Queue()
        self._main_actions = queue.Queue()
        self._tk_ready = threading.Event()
        self._tk_lock = threading.Lock()
        self._tk_started = False

        self.root = None
        self.ui_scale = 1.0
        self.osd = None

        # --- pywebview state (runs on MainThread) -------------------------
        self._webview = None
        self._webview_window = None
        self._webview_started = False
        self._webview_starting = False
        self._webview_lock = threading.Lock()
        self._eval_lock = threading.Lock()

        # --- state monitor & system tray (FIRST — this is the product) -----
        # 1.1.0: the tray icons are created before anything else; Tk/OSD
        # starts lazily on first use, so no GUI init blocks the tray.
        self._states = winapi.get_states()
        self.tray = Tray(self)
        self.monitor = Monitor(
            self._on_key_change, self.settings.get("poll_ms", 150)
        )
        self.monitor.start()

        # --- single-instance activation -----------------------------------
        if IS_WINDOWS and not dev:
            winapi.create_activation_event()
            winapi.watch_activation_event(self.open_settings_async)

        self.tray.start()

        if open_settings or dev or not IS_WINDOWS:
            self.open_settings_async()
        elif not getattr(self.tray, "healthy", False):
            # No tray icon could be created at all — without this the app
            # would be an invisible, uncontrollable background process.
            # The settings window (with its Quit button) is the fallback
            # control surface. (1.0.3)
            selfcheck.log(
                "app: tray unavailable — opening settings window as the "
                "control surface"
            )
            self.open_settings_async()

    # ==================================================================
    # Dedicated Tkinter Thread (OSD host & non-blocking task pump)
    # 1.1.0: started lazily on the first post() — the tkinter import and
    # the Tcl interpreter creation never sit on the startup critical path.
    # ==================================================================

    def _ensure_tk_thread(self):
        with self._tk_lock:
            if self._tk_started:
                return
            self._tk_started = True
        threading.Thread(
            target=self._run_tk_thread, name="tk-osd-thread", daemon=True
        ).start()

    def _run_tk_thread(self):
        try:
            # Deferred imports: tkinter + OSD are only needed once something
            # has to be shown on screen (first key toggle / preview).
            import tkinter as tk
            from .osd import OSD

            root = tk.Tk()
            root.withdraw()
            root.title(APP_NAME)
            root.protocol("WM_DELETE_WINDOW", lambda: None)
            try:
                ic = assets.icon_path("app.ico")
                if os.path.exists(ic):
                    root.iconbitmap(ic)
            except Exception:
                pass

            scale = winapi.enable_hidpi(root)
            if not (0.8 <= scale <= 2.5):
                scale = 1.0

            self.root = root
            self.ui_scale = scale
            self.osd = OSD(root, scale)
            self._tk_ready.set()

            root.after(40, self._pump_tasks)
            root.mainloop()
        except Exception as e:
            selfcheck.log("tk thread failed", e)
            self._tk_ready.set()

    def post(self, fn):
        """Schedule a callable on the Tkinter/OSD thread (lazy-started)."""
        if self._running:
            self._ensure_tk_thread()
            self._tasks.put(fn)

    def _pump_tasks(self):
        if not self._running or self.root is None:
            return
        while True:
            try:
                fn = self._tasks.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception as e:
                selfcheck.log("task error", e)
        if self._running and self.root is not None:
            try:
                self.root.after(40, self._pump_tasks)
            except Exception:
                pass

    # ==================================================================
    # Key events
    # ==================================================================

    def get_states(self):
        if self.monitor:
            return self.monitor.get_states()
        return dict(self._states)

    def _on_key_change(self, kid, on):
        self._states = self.get_states()
        if self.tray:
            self.tray.request_refresh()
        self._push_states()

        s = self.settings
        if not s.get("enabled", True):
            return
        k = s["keys"].get(kid)
        if not k or not k.get("enabled"):
            return
        if s["osd"]["enabled"]:
            self.post(lambda: self._osd_show(kid, on))
        if s["sound"]["enabled"]:
            name = s["sound"]["on_sound"] if on else s["sound"]["off_sound"]
            if name != "none":
                sound.play(name, s["sound"]["volume"])
        if s.get("balloon"):
            msg = tr("osd_turned_on" if on else "osd_turned_off").format(
                strings.key_name(kid)
            )
            self.tray.notify(APP_NAME, msg)

    def _osd_show(self, kid, on):
        if not self.osd:
            return
        s = self.settings
        k = s["keys"][kid]
        self.osd.show(
            kid,
            on,
            k,
            s["osd"]["position"],
            s["osd"]["duration_ms"],
            s["osd"]["scale"],
            (s["osd"]["custom_x"], s["osd"]["custom_y"]),
        )

    def toggle_key(self, kid):
        winapi.toggle_key(kid)
        if self.monitor:
            self.monitor.request_recheck(50)

    def show_osd_preview(self, kid=None):
        if not self.osd:
            return
        s = self.settings
        if kid is None:
            kid = "num" if s["keys"]["num"]["enabled"] else "caps"
        k = s["keys"][kid]
        self.osd.preview(
            kid,
            not self.get_states().get(kid, False),
            k,
            s["osd"]["position"],
            s["osd"]["scale"],
            (s["osd"]["custom_x"], s["osd"]["custom_y"]),
        )

    def preview_osd_from_tray(self):
        self.post(self.show_osd_preview)

    def start_osd_arrange(self):
        s = self.settings
        kid = "num" if s["keys"]["num"]["enabled"] else "caps"
        k = s["keys"][kid]

        def on_save(pos):
            fx, fy = pos
            s["osd"]["position"] = "custom"
            s["osd"]["custom_x"] = round(fx, 4)
            s["osd"]["custom_y"] = round(fy, 4)
            config.save(s, force=True)
            self._push_states()

        self.post(
            lambda: self.osd and self.osd.arrange(
                kid, k, s["osd"]["scale"], on_save=on_save
            )
        )

    # ==================================================================
    # Settings window (pywebview / WebView2 on MainThread)
    # ==================================================================

    def open_settings_async(self):
        self._main_actions.put("open_settings")
        # If webview is already running, also trigger show on a worker thread
        if self._webview_started and self._webview_window is not None:
            threading.Thread(
                target=self._show_existing_window, daemon=True
            ).start()

    def _show_existing_window(self):
        win = self._webview_window
        if win is None:
            return
        try:
            win.show()
            win.restore()
            self._push_states()
        except Exception as e:
            selfcheck.log("show existing webview window failed", e)

    def open_settings(self):
        self.open_settings_async()

    def _start_or_show_webview_on_main(self):
        if not self._running:
            return

        if self._webview_window is not None and self._webview_started:
            self._show_existing_window()
            return

        with self._webview_lock:
            if self._webview_starting or self._webview_started:
                return
            self._webview_starting = True

        if IS_WINDOWS and not winapi.has_webview2():
            with self._webview_lock:
                self._webview_starting = False
            res = winapi.message_box(
                tr("webview2_missing"), tr("webview2_missing_title"), 0x24
            )
            if res == 6:
                winapi.open_url(winapi.WEBVIEW2_DOWNLOAD)
            return

        try:
            import webview
        except Exception as e:
            with self._webview_lock:
                self._webview_starting = False
            self._settings_failed(e)
            return

        self._webview = webview
        try:
            webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True
        except Exception:
            pass

        from .bridge import Bridge
        self._bridge = Bridge(self)

        index_path = os.path.join(WEBUI_DIR, "index.html")
        if not os.path.exists(index_path):
            with self._webview_lock:
                self._webview_starting = False
            self._settings_failed(
                RuntimeError("webui index.html not found: %s" % index_path)
            )
            return

        title = (
            "%s — %s" % (APP_NAME, tr("tray_settings"))
            if strings.LANG == "fa"
            else "%s — Settings" % APP_NAME
        )
        bg = (
            "#0b0f17"
            if self.settings.get("theme", "dark") == "dark"
            else "#eef1f7"
        )

        try:
            window = webview.create_window(
                title=title,
                url=index_path,
                js_api=self._bridge,
                width=1000,
                height=700,
                min_size=(780, 580),
                background_color=bg,
                frameless=True,
                easy_drag=False,
                text_select=False,
                resizable=True,
            )
        except Exception as e:
            with self._webview_lock:
                self._webview_starting = False
            self._settings_failed(e)
            return

        def _on_closing():
            if not self._running:
                return True
            # Hide asynchronously so we never deadlock WinForms FormClosing
            threading.Timer(0.02, self.close_settings_window).start()
            return False

        window.events.closing += _on_closing
        self._webview_window = window
        with self._webview_lock:
            self._webview_started = True
            self._webview_starting = False

        try:
            if IS_WINDOWS:
                webview.start(gui="edgechromium", debug=False)
            else:
                webview.start(debug=False)
        except Exception as e:
            self._settings_failed(e)
        finally:
            with self._webview_lock:
                self._webview_started = False
                self._webview_starting = False
                self._webview_window = None

    def _settings_failed(self, err):
        selfcheck.log("settings window failed", err)
        winapi.message_box(tr("ui_failed"), tr("ui_failed_title"), 0x10)

    def close_settings_window(self):
        win = self._webview_window
        if win is not None:
            def _hide():
                try:
                    win.hide()
                except Exception as e:
                    selfcheck.log("window.hide error", e)
            threading.Thread(target=_hide, daemon=True).start()

    def minimize_settings_window(self):
        win = self._webview_window
        if win is not None:
            def _min():
                try:
                    win.minimize()
                except Exception as e:
                    selfcheck.log("window.minimize error", e)
            threading.Thread(target=_min, daemon=True).start()

    def _safe_eval_js(self, script):
        win = self._webview_window
        if win is None or not self._webview_started:
            return

        def _go():
            if not self._eval_lock.acquire(blocking=False):
                return
            try:
                win.evaluate_js(script)
            except Exception:
                pass
            finally:
                self._eval_lock.release()

        threading.Thread(target=_go, daemon=True).start()

    def _push_states(self):
        if self._webview_window is None or not self._webview_started:
            return
        payload = json.dumps({"states": self.get_states()})
        self._safe_eval_js(
            "window.__push && window.__push(%s)" % payload
        )

    # ==================================================================
    # Settings round-trip confirmation
    # ==================================================================

    def on_settings_saved(self, ok=True, message=""):
        if self._webview_window is None or not self._webview_started:
            return
        payload = json.dumps({"ok": bool(ok), "message": message})
        self._safe_eval_js(
            "window.__saved && window.__saved(%s)" % payload
        )

    def on_settings_changed(self):
        if self.tray:
            self.tray.request_refresh()
        if self.monitor:
            self.monitor.set_poll_ms(self.settings.get("poll_ms", 150))
        self._push_states()

    def apply_settings(self, fresh):
        self.settings = fresh
        strings.set_language(fresh.get("language", "fa"))
        config.save(fresh, force=True)
        self.on_settings_changed()

    # ==================================================================
    # Lifecycle
    # ==================================================================

    def quit(self):
        if not self._running:
            return
        self._running = False
        self._main_actions.put("quit")

        try:
            if self.monitor:
                self.monitor.stop()
        except Exception:
            pass
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass
        try:
            if self.osd and self.root:
                self.root.after(0, self.osd.hide)
        except Exception:
            pass
        try:
            if self._webview_window is not None:
                self._webview_window.destroy()
        except Exception:
            pass
        try:
            if self.root is not None:
                self.root.after(0, self._destroy_root)
        except Exception:
            pass

        def _force_exit():
            time.sleep(0.4)
            try:
                import ctypes
                if IS_WINDOWS:
                    ctypes.windll.kernel32.ExitProcess(0)
            except Exception:
                pass
            os._exit(0)

        threading.Thread(target=_force_exit, daemon=True).start()

    def _destroy_root(self):
        try:
            if self.root is not None:
                self.root.quit()
                self.root.destroy()
        except Exception:
            pass

    def run(self):
        """MainThread loop: waits for settings activation or quit signal."""
        while self._running:
            try:
                action = self._main_actions.get(timeout=0.25)
            except queue.Empty:
                continue
            if action == "quit" or not self._running:
                break
            if action == "open_settings":
                # Blocks on MainThread while pywebview is active
                self._start_or_show_webview_on_main()

        try:
            import ctypes
            if IS_WINDOWS:
                ctypes.windll.kernel32.ExitProcess(0)
        except Exception:
            pass
        os._exit(0)


# ======================================================================
# main()
# ======================================================================

def _safe_print(text):
    try:
        if sys.stdout is not None:
            print(text)
    except Exception:
        pass


def _background_selfcheck():
    """Run the full self-check after startup; surface fatal issues only."""
    try:
        problems, fatal = selfcheck.run()
        if fatal:
            selfcheck.log("selfcheck: fatal problem(s) after start")
            try:
                msgs = "\n".join(m for lv, m in problems if lv == "fatal")
                winapi.message_box(
                    msgs, "%s — %s" % (APP_NAME, tr("startup_error")), 0x10
                )
            except Exception:
                pass
    except Exception as e:
        try:
            selfcheck.log("background selfcheck crashed", e)
        except Exception:
            pass


def _prewarm_webview():
    """Import pywebview on a worker thread so opening Settings is fast."""
    try:
        t0 = time.perf_counter()
        import webview  # noqa: F401 — side-effect import only
        selfcheck.log(
            "startup: webview pre-warmed in %d ms"
            % int((time.perf_counter() - t0) * 1000)
        )
    except Exception as e:
        # Not fatal: the settings path retries the import on demand.
        selfcheck.log("startup: webview pre-warm failed", e)


def main(argv=None):
    argv = list(argv if argv is not None else [])

    if "--version" in argv:
        _safe_print("%s %s" % (APP_NAME, APP_VERSION))
        return 0
    if "--check" in argv:
        problems, fatal = selfcheck.run(full=True)
        lines = ["[%s] %s" % (level, msg) for level, msg in problems]
        if not problems:
            lines.append("All checks passed.")
        lines.append("Log file: %s" % (selfcheck.log_path() or "n/a"))
        text = "\n".join(lines)
        _safe_print(text)
        if sys.stdout is None:
            winapi.message_box(
                text, "%s — check" % APP_NAME, 0x10 if fatal else 0x40
            )
        return 1 if fatal else 0
    if "--reset" in argv:
        config.reset()
        _safe_print("Settings reset.")
        return 0

    dev = ("--dev" in argv) or not IS_WINDOWS
    open_settings = "--settings" in argv

    # 1.1.0: the self-check no longer runs on the startup critical path.
    # It used to import pywebview there (which drags in bottle/ssl/...),
    # adding seconds of dead time before the tray appeared on EVERY
    # launch. The full check now runs in a background thread right after
    # the app is up; only the explicit ``--check`` command still runs it
    # synchronously with the deepest probes.

    if not dev and not winapi.acquire_single_instance():
        if not winapi.signal_activation():
            winapi.message_box(
                tr("already_running"), tr("already_running_title"), 0x40
            )
        return 0

    if not IS_WINDOWS:
        _safe_print(tr("windows_only"))

    app = App(dev=dev, open_settings=open_settings)

    # Full environment self-check in the background — writes the session
    # log, pre-imports arabic_reshaper/python-bidi so the first Persian
    # OSD is instant, and never delays the tray.
    threading.Thread(target=_background_selfcheck, daemon=True).start()

    # Pre-load pywebview in the background so that the FIRST click on
    # "Settings" opens quickly instead of paying the whole import cost
    # at that moment. Importing on a worker thread is safe — only
    # webview.start() is restricted to the main thread.
    if IS_WINDOWS:
        threading.Timer(1.5, _prewarm_webview).start()

    if "--autoquit" in argv:
        ms = 1500
        for i, a in enumerate(argv):
            if a == "--autoquit" and i + 1 < len(argv) and argv[i + 1].isdigit():
                ms = int(argv[i + 1])
        threading.Timer(ms / 1000.0, app.quit).start()

    app.run()
    return 0