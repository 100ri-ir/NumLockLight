# -*- coding: utf-8 -*-
"""Thin, safe wrappers around Windows APIs (no-op / simulated off-Windows)."""
import ctypes
import os
import sys
import threading

from .constants import APP_ID, IS_WINDOWS, KEYS, RUN_KEY

_IS_WIN = IS_WINDOWS

# --------------------------------------------------------------------------
# Key states
# --------------------------------------------------------------------------
_vk = {}
if _IS_WIN:
    _user32 = ctypes.windll.user32
    _user32.GetKeyState.argtypes = [ctypes.c_int]
    _user32.GetKeyState.restype = ctypes.c_short
    _user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    _user32.GetAsyncKeyState.restype = ctypes.c_short
else:
    _fake_states = {"num": True, "caps": False, "scroll": False, "insert": False}


def get_state(key_id):
    """Toggle state (True = on) of a lock key.

    GetKeyState is authoritative for toggle bits when called from a thread
    that pumps messages — our monitor thread does exactly that.
    """
    if _IS_WIN:
        try:
            return bool(_user32.GetKeyState(KEYS[key_id]["vk"]) & 1)
        except Exception:
            return False
    return _fake_states.get(key_id, False)


def set_fake_state(key_id, value):
    if not _IS_WIN:
        _fake_states[key_id] = bool(value)


def get_states():
    return {kid: get_state(kid) for kid in KEYS}


def toggle_key(key_id):
    """Physically toggle a lock key via SendInput (keybd_event fallback)."""
    if not _IS_WIN:
        set_fake_state(key_id, not get_state(key_id))
        return True
    try:
        vk = KEYS[key_id]["vk"]
        ext = 0x0001 if KEYS[key_id]["ext"] else 0
        up = 0x0002
        try:
            # SendInput with a KEYBDINPUT struct — 1 down + 1 up
            class _KI(ctypes.Structure):
                _fields_ = [("wVk", ctypes.c_ushort),
                            ("wScan", ctypes.c_ushort),
                            ("dwFlags", ctypes.c_ulong),
                            ("time", ctypes.c_ulong),
                            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

            class _INPUT(ctypes.Structure):
                _fields_ = [("type", ctypes.c_ulong), ("ki", _KI)]

            def mk(vk, flags):
                inp = _INPUT()
                inp.type = 1  # INPUT_KEYBOARD
                inp.ki.wVk = vk
                inp.ki.dwFlags = flags
                return inp

            arr = (_INPUT * 2)(mk(vk, ext), mk(vk, ext | up))
            ctypes.windll.user32.SendInput(2, arr, ctypes.sizeof(_INPUT))
        except Exception:
            ctypes.windll.user32.keybd_event(vk, 0x45, ext, 0)
            ctypes.windll.user32.keybd_event(vk, 0x45, ext | up, 0)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# Monitor geometry (precise OSD placement)
# --------------------------------------------------------------------------

class MONITORINFO(ctypes.Structure):
    if _IS_WIN:
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", ctypes.c_long * 4),
            ("rcWork", ctypes.c_long * 4),
            ("dwFlags", ctypes.c_ulong),
        ]


def _point():
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    return POINT()


if _IS_WIN:
    _user32.GetCursorPos.argtypes = [ctypes.POINTER(type(_point()))]


def cursor_pos():
    """Current cursor position in physical screen coordinates."""
    if not _IS_WIN:
        return (0, 0)
    pt = _point()
    try:
        if _user32.GetCursorPos(ctypes.byref(pt)):
            return (pt.x, pt.y)
    except Exception:
        pass
    return (0, 0)


def work_area():
    """Work area (taskbar excluded) of the monitor under the cursor.

    Returns dict(x, y, w, h) in physical pixels. Falls back to the primary
    monitor work area on any failure.
    """
    if not _IS_WIN:
        return {"x": 0, "y": 0, "w": 1920, "h": 1040}
    try:
        cx, cy = cursor_pos()
        hmon = _user32.MonitorFromPoint(
            ctypes.c_long(cx), ctypes.c_long(cy), 2)  # MONITOR_DEFAULTTONEAREST
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if _user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            l, t, r, b = mi.rcWork
            return {"x": int(l), "y": int(t), "w": int(r - l), "h": int(b - t)}
    except Exception:
        pass
    try:
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        rc = RECT()
        if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rc), 0):  # SPI_GETWORKAREA
            return {"x": rc.left, "y": rc.top,
                    "w": rc.right - rc.left, "h": rc.bottom - rc.top}
    except Exception:
        pass
    return {"x": 0, "y": 0, "w": 1920, "h": 1040}


# --------------------------------------------------------------------------
# Run at startup (HKCU)
# --------------------------------------------------------------------------


def startup_command():
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    launcher = os.path.join(root, "NumLockLight.exe")
    if os.path.exists(launcher):
        return '"%s"' % launcher
    py = sys.executable
    if py.lower().endswith(("python.exe", "pythonw.exe")):
        candidate = py[:-10] + "pythonw.exe"
        if os.path.exists(candidate):
            py = candidate
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__main__.py")
    return '"%s" "%s"' % (py, script)


def get_startup():
    if not _IS_WIN:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE) as key:
            winreg.QueryValueEx(key, APP_ID)
            return True
    except Exception:
        return False


def set_startup(enabled):
    """Returns (ok, error_message)."""
    if not _IS_WIN:
        return True, ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_ID)
                except FileNotFoundError:
                    pass
        return True, ""
    except Exception as e:
        return False, str(e)


# --------------------------------------------------------------------------
# Single instance mutex + activation event (1.0.1)
# --------------------------------------------------------------------------
# v1.0.0 created a "Global\" mutex: that spans ALL user sessions, so a
# second user on fast-user-switching could not start their own instance.
# Per-user is the correct semantics for a tray app → "Local\" namespace.
# The new *activation event* lets a second instance wake the FIRST one
# (open/focus its settings window) instead of just showing a message box.
#
# 1.0.3 fix: the old code read GetLastError() through the SHARED
# ctypes.windll loader, whose own bookkeeping can clobber the thread's
# Win32 last-error between the CreateMutexW call and the GetLastError
# call — yielding random "already running" false positives (app exits
# instantly) or missed second instances. All kernel32 calls now go
# through a private WinDLL(use_last_error=True) with explicit argtypes/
# restypes, and the error is read with ctypes.get_last_error().
_MUTEX_HANDLE = None
_ACTIVATE_EVENT_NAME = "Local\\" + APP_ID + "_activate"
_ACTIVATE_EVENT = None

INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002

_k32 = None


def _kernel32():
    """Private kernel32 binding with proper last-error semantics."""
    global _k32
    if _k32 is None:
        _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        _k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        _k32.CreateMutexW.restype = ctypes.c_void_p
        _k32.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p]
        _k32.CreateEventW.restype = ctypes.c_void_p
        _k32.OpenEventW.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_wchar_p]
        _k32.OpenEventW.restype = ctypes.c_void_p
        _k32.SetEvent.argtypes = [ctypes.c_void_p]
        _k32.SetEvent.restype = ctypes.c_int
        _k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        _k32.WaitForSingleObject.restype = ctypes.c_uint
        _k32.CloseHandle.argtypes = [ctypes.c_void_p]
        _k32.CloseHandle.restype = ctypes.c_int
    return _k32


def acquire_single_instance():
    global _MUTEX_HANDLE
    if not _IS_WIN:
        return True
    try:
        k32 = _kernel32()
        handle = k32.CreateMutexW(None, False, "Local\\" + APP_ID)
        err = ctypes.get_last_error()
        if not handle:
            # could not create the mutex — fail open rather than block the app
            return True
        _MUTEX_HANDLE = handle
        return err != ERROR_ALREADY_EXISTS
    except Exception:
        return True


def create_activation_event():
    """First instance: create the named resettable event (auto-reset)."""
    global _ACTIVATE_EVENT
    if not _IS_WIN:
        return None
    try:
        k32 = _kernel32()
        _ACTIVATE_EVENT = k32.CreateEventW(None, False, False, _ACTIVATE_EVENT_NAME)
        return _ACTIVATE_EVENT
    except Exception:
        return None


def watch_activation_event(on_activate, poll_ms=250):
    """Call `on_activate()` whenever another instance signals the event.

    Runs on a daemon thread; never blocks startup. WaitForSingleObject on
    an auto-reset event consumes the signal, so no ResetEvent is needed.
    """
    if not _IS_WIN or not _ACTIVATE_EVENT:
        return None

    def _watch():
        k32 = _kernel32()
        while True:
            try:
                if k32.WaitForSingleObject(_ACTIVATE_EVENT, poll_ms) == WAIT_OBJECT_0:
                    try:
                        on_activate()
                    except Exception:
                        pass
            except Exception:
                pass

    t = threading.Thread(target=_watch, name="activation-watch", daemon=True)
    t.start()
    return t


def signal_activation():
    """Second instance: wake the running first instance. True if signalled."""
    if not _IS_WIN:
        return False
    try:
        k32 = _kernel32()
        handle = k32.OpenEventW(EVENT_MODIFY_STATE, False, _ACTIVATE_EVENT_NAME)
        if not handle:
            return False
        ok = bool(k32.SetEvent(handle))
        k32.CloseHandle(handle)
        return ok
    except Exception:
        return False


# --------------------------------------------------------------------------
# WebView2 runtime detection (needed by the settings window)
# --------------------------------------------------------------------------


def has_webview2():
    """True when the Microsoft Edge WebView2 runtime is installed."""
    if not _IS_WIN:
        return True  # dev mode: pretend it's fine
    try:
        import winreg
        guids = (
            "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",  # runtime
            "{2CD8A007-E189-409D-A2C8-9AF4EF3C72AA}",  # beta
            "{0D50BFEC-CD6A-4F9A-964C-C7416E3ACB10}",  # dev
            "{65C35B14-6C1D-4122-AC46-7148CC9D6497}",  # canary
        )
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for sub in (r"Software\Microsoft\EdgeUpdate\Clients",
                        r"Software\WOW6432Node\Microsoft\EdgeUpdate\Clients"):
                for guid in guids:
                    try:
                        with winreg.OpenKey(hive, sub + "\\" + guid) as k:
                            ver, _t = winreg.QueryValueEx(k, "pv")
                            if ver and ver != "0.0.0.0":
                                return True
                    except OSError:
                        continue
    except Exception:
        pass
    return False


WEBVIEW2_DOWNLOAD = "https://developer.microsoft.com/microsoft-edge/webview2/"


# --------------------------------------------------------------------------
# DPI awareness
# --------------------------------------------------------------------------


def enable_hidpi(root):
    """Make the process DPI-aware. Returns the scale factor."""
    scale = 1.0
    if not _IS_WIN:
        return scale
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system aware
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
        hdc = ctypes.windll.user32.GetDC(0)
        try:
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        finally:
            ctypes.windll.user32.ReleaseDC(0, hdc)
        if not dpi or dpi < 24:
            dpi = 96
        scale = dpi / 96.0
        try:
            root.tk.call("tk", "scaling", dpi / 72.0)
        except Exception:
            pass
    except Exception:
        scale = 1.0
    return scale


# --------------------------------------------------------------------------
# Misc helpers
# --------------------------------------------------------------------------


def message_box(text, title, flags=0x40):
    """Native MessageBoxW (works before/independently of any UI toolkit)."""
    if not _IS_WIN:
        print("[%s] %s" % (title, text.replace("\n", " | ")))
        return
    try:
        ctypes.windll.user32.MessageBoxW(None, str(text), str(title), flags | 0x1000)
    except Exception:
        pass


def open_url(url):
    import webbrowser
    try:
        webbrowser.open(url)
    except Exception:
        pass


def windows_version_text():
    if not _IS_WIN:
        return "Dev (non-Windows)"
    try:
        v = sys.getwindowsversion()
        return "Windows %d.%d (build %d)" % (v.major, v.minor, v.build)
    except Exception:
        return "Windows"
