# -*- coding: utf-8 -*-
"""On-screen display (OSD) — precise positioning + drag-to-place.

Fixes in 1.0.2:
- Fixed z-order in `arrange()` where `create_rectangle` was drawn on top
  of `create_text`, hiding the Persian drag hint.
- Uses Vazirmatn font registered via GDI and Pillow rendering.
"""
import tkinter as tk

from . import icons, strings, winapi
from .constants import IS_WINDOWS

try:
    from PIL import ImageTk
    _PIL_OK = True
except Exception:
    _PIL_OK = False

TRANSPARENT_KEY = "#010203"


class OSD:
    FADE_IN_MS = 130
    FADE_OUT_MS = 240

    def __init__(self, root, ui_scale=1.0):
        self.root = root
        self.ui_scale = max(0.75, min(2.5, ui_scale or 1.0))
        self.win = None
        self.canvas = None
        self._photo = None
        self._jobs = []
        self._arranging = False
        self._arrange_anchor = None
        self._arrange_win_size = None

    # -- window management ------------------------------------------------

    def _ensure_window(self):
        if self.win is not None and self.win.winfo_exists():
            return self.win
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        if IS_WINDOWS:
            try:
                win.attributes("-transparentcolor", TRANSPARENT_KEY)
            except tk.TclError:
                pass
        win.withdraw()
        self.win = win
        self.canvas = tk.Canvas(
            win,
            highlightthickness=0,
            bd=0,
            bg=TRANSPARENT_KEY if IS_WINDOWS else "#000000",
        )
        self.canvas.pack(fill="both", expand=True)
        return win

    @staticmethod
    def _set_click_through(hwnd, enabled):
        """Make the OSD ignore (or accept) mouse interaction."""
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if enabled:
                style |= (
                    WS_EX_TRANSPARENT
                    | WS_EX_NOACTIVATE
                    | WS_EX_TOOLWINDOW
                    | WS_EX_LAYERED
                )
            else:
                style &= ~(WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception:
            pass

    def _hwnd(self):
        try:
            import ctypes
            hwnd = self.win.winfo_id()
            parent = ctypes.windll.user32.GetParent(hwnd)
            return parent or hwnd
        except Exception:
            return None

    def _cancel_jobs(self):
        for j in self._jobs:
            try:
                self.root.after_cancel(j)
            except Exception:
                pass
        self._jobs = []

    def _after(self, ms, fn):
        j = self.root.after(ms, fn)
        self._jobs.append(j)
        return j

    # -- geometry ----------------------------------------------------------

    def _place(self, w, h, position="bottom_center", custom=(0.5, 0.92)):
        wa = winapi.work_area()
        margin = max(16, int(wa["h"] * 0.035))
        cx = wa["x"] + (wa["w"] - w) // 2
        cy = wa["y"] + (wa["h"] - h) // 2
        pos = position or "bottom_center"
        if pos == "custom":
            fx, fy = custom
            x = int(wa["x"] + fx * (wa["w"] - w))
            y = int(wa["y"] + fy * (wa["h"] - h))
        else:
            if pos.startswith("bottom"):
                y = wa["y"] + wa["h"] - h - margin
            elif pos.startswith("top"):
                y = wa["y"] + margin
            else:
                y = cy
            if pos.endswith("right"):
                x = wa["x"] + wa["w"] - w - margin
            elif pos.endswith("left"):
                x = wa["x"] + margin
            else:
                x = cx
        x = max(wa["x"], min(x, wa["x"] + wa["w"] - w))
        y = max(wa["y"], min(y, wa["y"] + wa["h"] - h))
        return x, y, wa

    # -- public API ---------------------------------------------------------

    def show(
        self,
        key_id,
        on,
        key_settings,
        position="bottom_center",
        duration_ms=1200,
        scale=1.0,
        custom=(0.5, 0.92),
        lang=None,
    ):
        if not _PIL_OK or self._arranging:
            return
        win = self._ensure_window()
        self._cancel_jobs()
        self._clear_arrange_bindings()

        img, (w, h) = icons.render_osd(key_id, on, key_settings, scale, lang)
        self._photo = ImageTk.PhotoImage(img)
        cv = self.canvas
        cv.configure(width=w, height=h)
        cv.delete("all")
        cv.create_image(0, 0, image=self._photo, anchor="nw")

        x, y, _wa = self._place(w, h, position, custom)
        dy = int(12 * scale) * (-1 if str(position).startswith("top") else 1)
        y0 = y - dy

        win.wm_geometry("%dx%d+%d+%d" % (w, h, x, y0))
        self._set_alpha(0.0)
        win.deiconify()
        win.lift()
        if IS_WINDOWS:
            hwnd = self._hwnd()
            if hwnd:
                self._set_click_through(hwnd, True)

        self._fade(0.0, 1.0, self.FADE_IN_MS, x, y0, y)
        self._after(max(300, duration_ms), self._fade_out)

    def preview(
        self,
        key_id,
        on,
        key_settings,
        position,
        scale=1.0,
        custom=(0.5, 0.92),
        lang=None,
    ):
        self.show(key_id, on, key_settings, position, 1800, scale, custom, lang)

    def hide(self):
        self._cancel_jobs()
        self._withdraw()

    # -- arrange mode ------------------------------------------------------

    def arrange(self, key_id, key_settings, scale=1.0, lang=None, on_save=None):
        """Show a persistent pill the user can drag; saves on release."""
        if not _PIL_OK:
            return
        win = self._ensure_window()
        self._cancel_jobs()
        self._arranging = True
        self._on_save_cb = on_save

        img, (w, h) = icons.render_osd(key_id, True, key_settings, scale, lang)
        self._photo = ImageTk.PhotoImage(img)
        cv = self.canvas
        total_h = h + int(34 * scale)
        cv.configure(width=w, height=total_h)
        cv.delete("all")
        cv.create_image(0, 0, image=self._photo, anchor="nw")

        hint = strings.shape(strings.tr("osd_drag_hint"))
        f = ("Vazirmatn", max(9, int(10 * scale)), "bold")
        try:
            # Draw background rectangle FIRST, then text on top
            cv.create_rectangle(
                4,
                h + 2,
                w - 4,
                h + int(30 * scale),
                fill="#111827",
                outline="#232c3f",
            )
            cv.create_text(
                w // 2,
                h + int(16 * scale),
                text=hint,
                font=f,
                fill="#dbe6ff",
                anchor="center",
            )
        except Exception:
            pass

        x, y, _wa = self._place(w, total_h, "custom", (0.5, 0.88))
        win.wm_geometry("%dx%d+%d+%d" % (w, total_h, x, y))
        self._set_alpha(0.95)
        win.deiconify()
        win.lift()
        if IS_WINDOWS:
            hwnd = self._hwnd()
            if hwnd:
                self._set_click_through(hwnd, False)

        self._bind_arrange(win, w, total_h)
        self._arrange_win_size = (w, total_h)

    def _bind_arrange(self, win, w, h):
        def on_press(ev):
            self._arrange_anchor = (
                ev.x_root - win.winfo_x(),
                ev.y_root - win.winfo_y(),
            )

        def on_motion(ev):
            if not self._arrange_anchor:
                return
            ax, ay = self._arrange_anchor
            win.wm_geometry("+%d+%d" % (ev.x_root - ax, ev.y_root - ay))

        def on_release(ev):
            self._save_arrange_position()

        def on_escape(ev):
            self.end_arrange(save=False)

        def on_double(ev):
            self._save_arrange_position()

        for seq, fn in (
            ("<ButtonPress-1>", on_press),
            ("<B1-Motion>", on_motion),
            ("<ButtonRelease-1>", on_release),
            ("<Double-Button-1>", on_double),
            ("<Escape>", on_escape),
            ("<Return>", on_release),
        ):
            try:
                win.bind(seq, fn)
                self.canvas.bind(seq, fn)
            except Exception:
                pass
        try:
            win.focus_force()
        except Exception:
            pass

    def _clear_arrange_bindings(self):
        if self.win is None or not self.win.winfo_exists():
            return
        for seq in (
            "<ButtonPress-1>",
            "<B1-Motion>",
            "<ButtonRelease-1>",
            "<Double-Button-1>",
            "<Escape>",
            "<Return>",
        ):
            try:
                self.win.unbind(seq)
                self.canvas.unbind(seq)
            except Exception:
                pass

    def _save_arrange_position(self):
        if not (self.win and self.win.winfo_exists()):
            return
        w = self.win.winfo_width()
        h = (
            self._arrange_win_size[1]
            if self._arrange_win_size
            else self.win.winfo_height()
        )
        x, y = self.win.winfo_x(), self.win.winfo_y()
        wa = winapi.work_area()
        fx = (x + w / 2.0 - wa["x"]) / float(wa["w"])
        fy = (y + h / 2.0 - wa["y"]) / float(wa["h"])
        fx = min(1.0, max(0.0, fx))
        fy = min(1.0, max(0.0, fy))
        self.end_arrange(save=True, pos=(fx, fy))

    def end_arrange(self, save=False, pos=None):
        cb = getattr(self, "_on_save_cb", None)
        self._arranging = False
        self._clear_arrange_bindings()
        self._cancel_jobs()
        self._withdraw()
        if save and cb and pos:
            try:
                cb(pos)
            except Exception:
                pass
        self._on_save_cb = None

    @property
    def arranging(self):
        return self._arranging

    # -- animation internals -----------------------------------------------

    def _withdraw(self):
        if self.win is not None and self.win.winfo_exists():
            self.win.withdraw()

    def _set_alpha(self, a):
        try:
            self.win.attributes("-alpha", max(0.0, min(1.0, a)))
        except tk.TclError:
            pass

    def _fade(self, a0, a1, ms, x, y0, y1):
        steps = 12
        delay = max(8, ms // steps)

        def step(i):
            t = (i + 1) / steps
            e = 1 - (1 - t) ** 3
            self._set_alpha(a0 + (a1 - a0) * e)
            yy = int(y0 + (y1 - y0) * e)
            try:
                self.win.wm_geometry("+%d+%d" % (x, yy))
            except Exception:
                pass
            if i + 1 < steps:
                self._after(delay, lambda: step(i + 1))

        step(0)

    def _fade_out(self):
        if self.win is None or not self.win.winfo_exists():
            return
        x = self.win.winfo_x()
        y = self.win.winfo_y()
        self._fade(1.0, 0.0, self.FADE_OUT_MS, x, y, y)
        self._after(self.FADE_OUT_MS + 40, self._withdraw)