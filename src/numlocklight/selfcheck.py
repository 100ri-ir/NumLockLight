# -*- coding: utf-8 -*-
"""Startup self-check + lightweight file logging — NumLock Light 1.1.0.

ROOT CAUSE this module fixes
----------------------------
v1.0.0 wrapped every tray/OSD code path in bare ``except Exception: pass``.
When a dependency was missing from the packaged EXE (or an asset failed to
load) the app started "successfully" with **no tray icon, no OSD and no
error anywhere** — an invisible, unkillable process. A background tray app
must fail *loudly* into a log file, because most of the time there is no
console attached (windowed PyInstaller builds have no stdout/stderr).

Usage
-----
* ``selfcheck.log(...)`` — timestamped line into ``<data dir>/NumLockLight.log``
  (portable mode: next to the EXE; installed mode: ``%APPDATA%\\NumLockLight``).
  The log is trimmed to the last ~200 lines at startup so it never grows
  unbounded.
* ``selfcheck.run()`` — probes the win32 pystray backend, Pillow + raqm,
  the reshaper pair, the sound engine, assets and WebView2; returns
  ``(problems, fatal)`` and logs a full environment dump. Since 1.1.0 this
  runs in a BACKGROUND thread after startup (it used to run on the startup
  critical path and import pywebview there — seconds of dead time before
  the tray appeared on every launch). In background mode pywebview is
  probed with ``importlib.util.find_spec`` (no execution, no bottle/ssl
  import); only ``run(full=True)`` — used by ``--check`` — really imports
  it.
* CLI: ``NumLockLight.exe --check`` runs the self-check and exits.
"""
import os
import sys
import time
import traceback

from .constants import APP_NAME, APP_VERSION, IS_WINDOWS, data_dir as _data_dir

_LOG_PATH = None
_session_marked = False


def log_path():
    global _LOG_PATH
    if _LOG_PATH is None:
        try:
            _LOG_PATH = os.path.join(_data_dir(), "NumLockLight.log")
        except Exception:
            _LOG_PATH = None
    return _LOG_PATH


def log(message, exc=None):
    """Append one timestamped line to the log file (never raises)."""
    global _session_marked
    path = log_path()
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not _session_marked:
            # trim: keep the last ~200 lines of the previous sessions
            _trim(path, keep_lines=200)
            _session_marked = True
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8", errors="replace") as f:
            f.write("[%s] %s\n" % (stamp, message))
            if exc is not None:
                f.write("    %s\n" % "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass


def _trim(path, keep_lines=200):
    try:
        if not os.path.exists(path) or os.path.getsize(path) < 32 * 1024:
            return
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.writelines(lines[-keep_lines:])
    except Exception:
        pass


# --------------------------------------------------------------------------
# Dependency probes
# --------------------------------------------------------------------------

def _probe_import(module_name):
    try:
        __import__(module_name)
        return True, None
    except Exception as e:  # ImportError and anything else that can surface
        return False, e


def _probe_spec(module_name):
    """Check that a module is present WITHOUT executing it (find_spec).

    Used for pywebview during background self-checks: importing it for real
    drags in bottle/ssl and more, which costs seconds — exactly what the
    1.1.0 startup fix removed from the critical path.
    """
    try:
        import importlib.util
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False, ImportError("module not found")
        return True, None
    except Exception as e:
        return False, e


def _probe_file(path):
    return os.path.exists(path)


def run(full=False):
    """Verify everything the app needs at runtime.

    Returns ``(problems, fatal)`` where *problems* is a list of
    ``(level, message)`` tuples and *fatal* is True when the app cannot
    be controlled at all (no tray AND no way to exit).

    ``full=True`` (used by ``--check``) also *executes* the pywebview
    import; the background startup check only verifies it is bundled.
    """
    from . import winapi
    from .constants import FONTS_DIR, ICONS_DIR, SOUNDS_DIR

    problems = []
    fatal = False

    log("=" * 60)
    log("%s %s self-check" % (APP_NAME, APP_VERSION))
    log("python %s on %s | frozen=%s | argv=%s" % (
        sys.version.split()[0], sys.platform,
        bool(getattr(sys, "frozen", False)), " ".join(sys.argv[:4])))

    # --- hard dependencies: the tray and the OSD renderer ----------------
    ok, err = _probe_import("pystray")
    log("pystray import: %s" % ("OK" if ok else "MISSING (%r)" % err))
    if not ok:
        problems.append(("fatal", "pystray is missing — no tray icon can be "
                                  "created. Reinstall the app."))
        fatal = fatal or IS_WINDOWS

    if ok:
        ok_backend, err = _probe_import("pystray._win32")
        log("pystray._win32 backend: %s" % ("OK" if ok_backend else
                                            "MISSING (%r)" % err))
        if IS_WINDOWS and not ok_backend:
            problems.append(("fatal", "pystray win32 backend missing from the "
                                      "package (PyInstaller hiddenimport)."))
            fatal = True

    ok, err = _probe_import("PIL")
    log("Pillow import: %s" % ("OK" if ok else "MISSING (%r)" % err))
    if not ok:
        problems.append(("fatal", "Pillow is missing — tray icons and the OSD "
                                  "cannot be rendered. Reinstall the app."))
        fatal = fatal or IS_WINDOWS
    else:
        try:
            from PIL import features
            log("Pillow raqm complex-text support: %s" %
                ("yes" if features.check("raqm") else "no"))
        except Exception:
            pass

    # --- Persian shaping pair (needed because Windows Pillow wheels have
    #     no raqm — python-pillow/Pillow#7126) ------------------------------
    ok_r, err_r = _probe_import("arabic_reshaper")
    ok_b, err_b = _probe_import("bidi.algorithm")
    log("arabic-reshaper: %s | python-bidi: %s" %
        ("OK" if ok_r else "MISSING", "OK" if ok_b else "MISSING"))
    if not (ok_r and ok_b):
        problems.append(("warn", "arabic-reshaper/python-bidi missing — "
                                 "Persian OSD text will render disconnected."))
        if ok_r and err_r is not None:
            log("arabic_reshaper probe: %r" % err_r)
        if not ok_b and err_b is not None:
            log("bidi probe: %r" % err_b)

    # --- settings window stack -------------------------------------------
    if full:
        ok, err = _probe_import("webview")
        log("pywebview import: %s" % ("OK" if ok else "MISSING (%r)" % err))
    else:
        ok, err = _probe_spec("webview")
        log(
            "pywebview bundled: %s (find_spec — not imported at startup)"
            % ("yes" if ok else "NO (%r)" % err)
        )
    if not ok:
        problems.append(("warn", "pywebview missing — the settings window "
                                 "will not open (tray/OSD keep working)."))
    if IS_WINDOWS:
        log("WebView2 runtime installed: %s" % winapi.has_webview2())
        if not winapi.has_webview2():
            problems.append(("warn", "WebView2 runtime not found — settings "
                                     "window will offer to download it."))

    # --- sound engine (1.1.0: ctypes winmm, winsound is no longer used) ---
    try:
        from . import sound as _sound
        _snd_ok = _sound.available()
        log("sound engine (winmm via ctypes): %s"
            % ("OK" if _snd_ok else "UNAVAILABLE"))
        if not _snd_ok:
            problems.append(("warn", "sound engine unavailable — effects "
                                     "will be silent."))
    except Exception as e:
        log("sound engine probe failed: %r" % (e,))
        problems.append(("warn", "sound engine probe failed — effects may "
                                 "be silent."))

    # --- assets actually used by the code ---------------------------------
    for fn in ("Vazirmatn-Regular.ttf", "Vazirmatn-SemiBold.ttf",
               "Vazirmatn-Bold.ttf"):
        p = os.path.join(FONTS_DIR, fn)
        if not _probe_file(p):
            problems.append(("warn", "font missing: %s" % fn))
    log("fonts dir (%s) present: %s" % (FONTS_DIR, _probe_file(FONTS_DIR)))
    for fn in ("app.ico", "lucide-keyboard.png"):
        p = os.path.join(ICONS_DIR, fn)
        if not _probe_file(p):
            problems.append(("warn", "icon asset missing: %s" % fn))
    log("icons dir (%s) present: %s" % (ICONS_DIR, _probe_file(ICONS_DIR)))
    n_sounds = 0
    try:
        n_sounds = len([f for f in os.listdir(SOUNDS_DIR) if f.endswith(".wav")])
    except Exception:
        pass
    log("bundled sounds: %d" % n_sounds)
    if n_sounds == 0:
        problems.append(("warn", "no sound files found (OSD sounds disabled)."))

    log("log file: %s" % log_path())
    log("self-check: %d problem(s), fatal=%s" % (len(problems), fatal))
    return problems, fatal
