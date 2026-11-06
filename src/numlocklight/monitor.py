# -*- coding: utf-8 -*-
"""Key-state monitor — instant AND accurate.

Strategy
--------
1. A dedicated thread installs a low-level keyboard hook
   (WH_KEYBOARD_LL). Every physical key press in the system passes
   through our callback instantly — including presses from remote
   desktops, on-screen keyboards, scripts and macros.
2. The same thread runs a Windows message pump, which makes
   GetKeyState()'s toggle bit authoritative when read from it.
3. After every relevant key-down we re-read the real state twice
   (+25 ms and +90 ms): the hook fires *before* the system flips the
   toggle bit, so reading with a small delay is what keeps the
   indicator 100% correct.
4. A slow safety poll (default 150 ms) catches anything else
   (e.g. state changed by other software without a key event we saw).

Fallback: if the hook cannot be installed, the thread still pumps
messages and polls at a faster rate (60 ms).
"""
import ctypes
import threading
import time

from .constants import IS_WINDOWS, KEYS
from . import winapi

if IS_WINDOWS:
    from ctypes import wintypes

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
LLKHF_INJECTED = 0x10


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    if IS_WINDOWS:
        _fields_ = [
            ("vkCode", wintypes.DWORD),
            ("scanCode", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_void_p),
        ]


class Monitor:
    """Watches the toggle keys and calls `on_change(key_id, on)` on every
    real state change, from its own thread."""

    def __init__(self, on_change, poll_ms=150):
        self.on_change = on_change
        self.poll_ms = max(60, int(poll_ms))
        self.states = winapi.get_states()
        self._running = True
        self._lock = threading.Lock()
        self._hook = None
        self._thread = None
        self._recheck_at = []          # timestamps for delayed re-reads
        self._recheck_lock = threading.Lock()
        self.hook_installed = False

    # ---------------------------------------------------------------- API --

    def start(self):
        self._thread = threading.Thread(target=self._run, name="key-monitor", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def get_states(self):
        with self._lock:
            return dict(self.states)

    def request_recheck(self, delay_ms=60):
        """Ask for a state re-read soon (used right after WE toggle a key)."""
        with self._recheck_lock:
            now = time.perf_counter()
            for d in (delay_ms / 1000.0, (delay_ms + 70) / 1000.0):
                if d not in self._recheck_at:
                    self._recheck_at.append(now + d)

    def set_poll_ms(self, ms):
        self.poll_ms = max(60, int(ms))

    # ------------------------------------------------------------- thread --

    def _run(self):
        if IS_WINDOWS:
            self._install_hook()
        # Message pump: required both for the hook and for reliable
        # GetKeyState toggle bits on this thread.
        msg = ctypes.wintypes.MSG() if IS_WINDOWS else None
        last_poll = 0.0
        while self._running:
            if IS_WINDOWS:
                try:
                    while ctypes.windll.user32.PeekMessageW(
                            ctypes.byref(msg), 0, 0, 0, 1):  # PM_REMOVE
                        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
                except Exception:
                    pass
            now = time.perf_counter()
            due = self._due_recheck(now)
            interval = 0.012 if self.hook_installed else min(0.06, self.poll_ms / 1000.0)
            if due or now - last_poll >= self.poll_ms / 1000.0:
                self._read_and_emit()
                last_poll = now
            time.sleep(interval)
        self._remove_hook()

    # -------------------------------------------------------------- hook ---

    def _install_hook(self):
        try:
            # LRESULT is LONG_PTR — 64-bit on x64 Windows. The old code used
            # c_long (32-bit) as the callback return type, which truncated
            # the value returned by CallNextHookEx and could corrupt the
            # hook chain's pass-through behaviour on 64-bit systems.
            LRESULT = ctypes.c_ssize_t

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.SetWindowsHookExW.argtypes = [
                ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_ulong]
            user32.SetWindowsHookExW.restype = ctypes.c_void_p
            user32.CallNextHookEx.argtypes = [
                ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM,
                ctypes.POINTER(_KBDLLHOOKSTRUCT)]
            user32.CallNextHookEx.restype = LRESULT
            user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
            user32.UnhookWindowsHookEx.restype = ctypes.c_int
            self._user32 = user32

            CTYPES = ctypes.WINFUNCTYPE(
                LRESULT, ctypes.c_int, wintypes.WPARAM,
                ctypes.POINTER(_KBDLLHOOKSTRUCT))

            def _proc(n_code, w_param, l_param):
                try:
                    if n_code == 0 and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        vk = l_param.contents.vkCode
                        for kid, meta in KEYS.items():
                            if meta["vk"] == vk:
                                # toggle flips right after this event —
                                # schedule two delayed authoritative reads
                                with self._recheck_lock:
                                    now = time.perf_counter()
                                    for d in (0.025, 0.090):
                                        if now + d not in self._recheck_at:
                                            self._recheck_at.append(now + d)
                                break
                except Exception:
                    pass
                return user32.CallNextHookEx(
                    self._hook, n_code, w_param, l_param)

            self._proc_ref = CTYPES(_proc)  # keep alive!
            self._hook = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL, self._proc_ref,
                ctypes.windll.kernel32.GetModuleHandleW(None), 0)
            self.hook_installed = bool(self._hook)
        except Exception:
            self.hook_installed = False

    def _remove_hook(self):
        if self._hook:
            try:
                u = getattr(self, "_user32", None) or ctypes.windll.user32
                u.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None

    # ------------------------------------------------------------- reads --

    def _due_recheck(self, now):
        with self._recheck_lock:
            if not self._recheck_at:
                return False
            due = any(t <= now for t in self._recheck_at)
            self._recheck_at = [t for t in self._recheck_at if t > now]
            return due

    def _read_and_emit(self):
        fresh = winapi.get_states()
        with self._lock:
            old = dict(self.states)
            self.states = dict(fresh)
        for kid, val in fresh.items():
            if old.get(kid) != val:
                try:
                    self.on_change(kid, val)
                except Exception:
                    pass
