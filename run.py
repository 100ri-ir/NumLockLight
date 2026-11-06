# -*- coding: utf-8 -*-
"""NumLock Light — run the app straight from the repository root.

Usage:
    python run.py                 # normal start (tray on Windows)
    python run.py --settings      # open the settings window
    python run.py --dev           # dev mode (non-Windows / screenshot runs)

1.1.0: the import of the app package happens INSIDE main() with a loud,
logged fallback — in a windowed (no-console) PyInstaller build a missing
module would otherwise die with no visible error at all.
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "src"))


def _crash_report(err):
    """Show + persist an import-time failure (windowed builds have no stderr)."""
    text = (
        "NumLock Light could not start.\n\n"
        "A required module is missing or damaged:\n%r\n\n"
        "Please reinstall the application." % (err,)
    )
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, text, "NumLock Light — startup error", 0x10
        )
    except Exception:
        pass
    try:
        import time
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = ROOT
        with open(
            os.path.join(base, "startup_crash.log"), "a",
            encoding="utf-8", errors="replace",
        ) as f:
            f.write("[%s] %r\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), err))
    except Exception:
        pass


def main(argv=None):
    try:
        from numlocklight.app import main as app_main
    except Exception as e:  # missing/damaged module in the frozen bundle
        _crash_report(e)
        return 1
    return app_main(list(argv if argv is not None else []))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
