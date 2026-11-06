# -*- coding: utf-8 -*-
"""Sound engine — bundled CC0 effects with per-playback volume.

1.1.0 ROOT-CAUSE FIX — every sound was silent
---------------------------------------------
The 1.0.x engine played scaled buffers through::

    winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_ASYNC)

CPython (3.13 and later — including the 3.15 this app ships with) raises
``RuntimeError: Cannot play asynchronously from memory`` for exactly that
flag combination, because the lifetime of an async-memory buffer cannot be
guaranteed by the ``winsound`` wrapper. The old engine swallowed that
exception with ``except Exception: pass`` — so **no sound ever played**
and nothing ever showed up in the log.

The engine now talks to ``winmm.dll`` directly via ctypes and does not
import ``winsound`` at all:

* volume >= 99 → the original .wav file, played with
  ``SND_FILENAME | SND_ASYNC | SND_NODEFAULT``. winmm streams the file
  from disk itself, so there is no buffer to keep alive.
* volume 1..98  → the PCM-scaled WAV image played with ``SND_MEMORY``
  (synchronous) inside the worker daemon thread — the buffer is a live
  local Python object held for the whole duration of the blocking call,
  so its lifetime is provably correct.
* volume <= 0   → treated as "muted", nothing is played.

Playback failures are logged (first few only) instead of being silently
swallowed.
"""
import ctypes
import io
import os
import struct
import threading
import time
import wave

from . import assets, selfcheck
from .constants import IS_WINDOWS

FILES = {
    "chime": "on-chime.wav",
    "glass": "on-glass.wav",
    "rise": "on-rise.wav",
    "select": "on-select.wav",
    "fall": "off-fall.wav",
    "tick": "off-tick.wav",
    "soft": "off-soft.wav",
    "click": "click.wav",
}

# winmm PlaySound flags
SND_ASYNC = 0x0001
SND_NODEFAULT = 0x0002
SND_MEMORY = 0x0004
SND_FILENAME = 0x00020000

_winmm = None
_winmm_error = None
_winmm_lock = threading.Lock()

_raw_cache = {}
_scaled_cache = {}
_keepalive = []
_keepalive_lock = threading.Lock()
_errors_logged = 0


def _engine():
    """Load winmm.dll exactly once. Returns the DLL or None (never raises)."""
    global _winmm, _winmm_error
    if _winmm is not None:
        return _winmm
    if _winmm_error is not None:
        return None
    with _winmm_lock:
        if _winmm is not None:
            return _winmm
        if _winmm_error is not None:
            return None
        if not IS_WINDOWS:
            _winmm_error = "not windows"
            return None
        try:
            lib = ctypes.WinDLL("winmm")
            lib.PlaySoundW.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
            ]
            lib.PlaySoundW.restype = ctypes.c_int
            _winmm = lib
        except Exception as e:
            _winmm_error = e
            selfcheck.log(
                "sound: winmm.dll could not be loaded — sounds disabled", e
            )
            return None
        return _winmm


def available():
    """True when the sound engine can play (winmm loaded)."""
    return _engine() is not None


def _read_bytes(path):
    data = _raw_cache.get(path)
    if data is None:
        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception:
            return None
        if len(_raw_cache) > 24:
            _raw_cache.clear()
        _raw_cache[path] = data
    return data


def _scale_wav(path, volume):
    """Read a 16-bit WAV and return its bytes with the gain applied.

    The result is cached per (path, rounded-gain) so repeated plays of the
    same effect at the same volume cost nothing.
    """
    try:
        gain = max(0.0, min(1.0, float(volume) / 100.0))
    except (TypeError, ValueError):
        gain = 1.0
    if gain >= 0.999:
        return _read_bytes(path)  # nothing to scale — play the original
    key = (path, int(round(gain * 100)))
    if key in _scaled_cache:
        return _scaled_cache[key]

    with wave.open(path, "rb") as w:
        params = w.getparams()
        nchannels = params.nchannels
        sampwidth = params.sampwidth
        framerate = params.framerate
        frames = w.readframes(params.nframes)
    if sampwidth != 2:
        # non-PCM16 file: cannot scale, play as-is
        return _read_bytes(path)

    count = len(frames) // 2
    samples = struct.unpack("<%dh" % count, frames[: count * 2])
    scaled = tuple(
        max(-32768, min(32767, int(s * gain))) for s in samples
    )
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(nchannels)
        out.setsampwidth(sampwidth)
        out.setframerate(framerate)
        out.writeframes(struct.pack("<%dh" % len(scaled), *scaled))
    data = buf.getvalue()

    if len(_scaled_cache) > 24:
        _scaled_cache.clear()
    _scaled_cache[key] = data
    return data


def _note_error(message):
    """Log the first few playback problems so they are diagnosable."""
    global _errors_logged
    if _errors_logged < 3:
        _errors_logged += 1
        selfcheck.log("sound: %s" % message)


def _play_path_async(path):
    """Play a .wav file asynchronously — winmm streams it from disk."""
    mmlib = _engine()
    if mmlib is None:
        return False
    try:
        cw = ctypes.c_wchar_p(os.fspath(path))
        ok = bool(
            mmlib.PlaySoundW(cw, None, SND_FILENAME | SND_ASYNC | SND_NODEFAULT)
        )
        # Keep the path object referenced for a while: winmm may still be
        # holding the pointer right after the async call returns.
        now = time.monotonic()
        with _keepalive_lock:
            _keepalive.append((now, cw))
            _keepalive[:] = [k for k in _keepalive if now - k[0] < 15.0]
        return ok
    except Exception as e:
        _note_error("file playback failed (%r)" % (e,))
        return False


def _play_memory_sync(data):
    """Play an in-memory WAV image; blocks the calling thread until done.

    ``create_string_buffer`` pins the bytes in a live Python object for the
    whole (synchronous) call — the buffer winmm reads from is therefore
    valid for the entire playback, unlike the async-memory case.
    """
    mmlib = _engine()
    if mmlib is None:
        return False
    try:
        buf = ctypes.create_string_buffer(bytes(data))
        return bool(mmlib.PlaySoundW(buf, None, SND_MEMORY | SND_NODEFAULT))
    except Exception as e:
        _note_error("memory playback failed (%r)" % (e,))
        return False


def play(name, volume=100):
    """Play a bundled effect asynchronously. Safe no-op off-Windows."""
    if not IS_WINDOWS:
        return False
    fn = FILES.get(name)
    if not fn:
        return False
    path = assets.sound_path(fn)
    if not os.path.exists(path):
        return False
    try:
        vol = int(float(volume))
    except (TypeError, ValueError):
        vol = 100
    if vol <= 0:
        return True  # muted by the user — nothing to do
    threading.Thread(target=_play_safe, args=(path, vol), daemon=True).start()
    return True


def play_file(path, volume=100):
    """Play a .wav file from disk (custom sound paths)."""
    if not IS_WINDOWS or not path or not os.path.exists(path):
        return False
    try:
        vol = int(float(volume))
    except (TypeError, ValueError):
        vol = 100
    if vol <= 0:
        return True  # muted by the user — nothing to do
    threading.Thread(
        target=_play_safe, args=(os.fspath(path), vol), daemon=True
    ).start()
    return True


def _play_safe(path, volume):
    try:
        if volume >= 99:
            ok = _play_path_async(path)
        else:
            data = _scale_wav(path, volume)
            ok = _play_memory_sync(data) if data else _play_path_async(path)
        if not ok:
            _note_error("PlaySoundW returned FALSE for %s" % path)
    except Exception as e:
        _note_error("playback error for %s (%r)" % (path, e))
