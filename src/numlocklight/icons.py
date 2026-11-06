# -*- coding: utf-8 -*-
"""Tray icon and OSD pill renderer using Pillow + Vazirmatn font."""
import base64
import io
import os

from PIL import Image, ImageDraw, ImageFont

from . import assets, strings
from .constants import GREEN, ICON_SIZES, IS_WINDOWS, KEYS, KEY_ORDER, RED

TRANSPARENT_RGB = (1, 2, 3)

_font_cache = {}
_raqm_checked = None


def _has_raqm():
    global _raqm_checked
    if _raqm_checked is None:
        try:
            from PIL import features
            _raqm_checked = bool(features.check("raqm"))
        except Exception:
            _raqm_checked = False
    return _raqm_checked


def _prep_text(text):
    """Shape Persian text only when Pillow does not have libraqm."""
    if not text:
        return ""
    if _has_raqm():
        return str(text)
    return strings.shape(str(text))


def _load_font(kind="bold", size=24):
    key = (kind, int(size))
    if key in _font_cache:
        return _font_cache[key]
    p = assets.font_path(kind)
    font = None
    if os.path.exists(p):
        try:
            font = ImageFont.truetype(p, int(size))
        except Exception:
            font = None
    if font is None:
        for fallback in ("Vazirmatn-Bold.ttf", "segoeui.ttf", "arialbd.ttf", "tahoma.ttf"):
            try:
                font = ImageFont.truetype(fallback, int(size))
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def _hex_to_rgb(h, default=(34, 197, 94)):
    try:
        s = str(h).strip().lstrip("#")
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        if len(s) == 6:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except Exception:
        pass
    return default


def _draw_centered_text(draw, box, text, font, fill=(255, 255, 255, 255)):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    try:
        draw.text((cx, cy), text, font=font, fill=fill, anchor="mm")
    except Exception:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw / 2.0, cy - th / 2.0 - bbox[1]), text, font=font, fill=fill)


def _render_style(kid, on, color_hex, style="badge", px=64):
    ss = 2
    S = px * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    rgb = _hex_to_rgb(color_hex, (34, 197, 94) if on else (239, 68, 68))
    meta = KEYS.get(kid, KEYS["num"])
    badge = meta["badge"]
    keycap = meta["keycap"]

    if style == "led":
        cx, cy = S // 2, S // 2
        r = int(S * 0.34)
        for i in range(4, 0, -1):
            gr = r + i * int(S * 0.035)
            d.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=rgb + (35,))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgb + (255,))
        hr = int(r * 0.38)
        hx, hy = cx - int(r * 0.28), cy - int(r * 0.28)
        d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=(255, 255, 255, 110))

    elif style == "ring":
        pad = int(S * 0.14)
        w = max(4, int(S * 0.11))
        d.ellipse([pad, pad, S - pad, S - pad], outline=rgb + (255,), width=w)
        ir = int(S * 0.16)
        cx, cy = S // 2, S // 2
        d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=rgb + (255 if on else 190,))

    elif style == "glow":
        cx, cy = S // 2, S // 2
        for frac, alpha in ((0.44, 45), (0.34, 90), (0.24, 240)):
            r = int(S * frac)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgb + (alpha,))
        cr = int(S * 0.09)
        d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(255, 255, 255, 240))

    elif style == "keycap":
        pad = int(S * 0.08)
        rad = int(S * 0.22)
        dark = tuple(max(0, c - 55) for c in rgb)
        d.rounded_rectangle([pad, pad + int(S * 0.06), S - pad, S - pad], radius=rad, fill=dark + (255,))
        d.rounded_rectangle([pad, pad, S - pad, S - pad - int(S * 0.06)], radius=rad, fill=rgb + (255,))
        f = _load_font("bold", int(S * (0.28 if len(keycap) > 3 else 0.33)))
        _draw_centered_text(d, (pad, pad, S - pad, S - pad - int(S * 0.06)), keycap, f)

    elif style == "icon":
        pad = int(S * 0.08)
        rad = int(S * 0.26)
        d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=rad, fill=rgb + (255,))
        glyph_path = assets.icon_path("lucide-keyboard.png")
        if os.path.exists(glyph_path):
            try:
                gs = int(S * 0.56)
                g = Image.open(glyph_path).convert("RGBA").resize((gs, gs), Image.LANCZOS)
                img.alpha_composite(g, ((S - gs) // 2, (S - gs) // 2 + int(S * 0.04)))
            except Exception:
                pass
        dot_r = int(S * 0.09)
        dx, dy = S - pad - int(S * 0.16), pad + int(S * 0.16)
        d.ellipse([dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r], fill=(255, 255, 255, 255))

    else:  # "badge" (default)
        pad = int(S * 0.08)
        rad = int(S * 0.27)
        d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=rad, fill=rgb + (255,))
        d.rounded_rectangle(
            [pad + 2, pad + 2, S - pad - 2, S - pad - 2],
            radius=rad,
            outline=(255, 255, 255, 55),
            width=max(2, S // 42),
        )
        f = _load_font("bold", int(S * 0.50))
        _draw_centered_text(d, (pad, pad, S - pad, S - pad), badge, f)

    return img.resize((px, px), Image.LANCZOS)


def tray_image(kid, on, key_settings, style="badge", size_name="md"):
    px = ICON_SIZES.get(size_name, 64)
    color = key_settings.get("color_on", GREEN) if on else key_settings.get("color_off", RED)
    return _render_style(kid, on, color, style, px)


def combined_tray_image(states, settings):
    size_name = settings.get("tray", {}).get("size", "md")
    px = ICON_SIZES.get(size_name, 64)
    ss = 2
    S = px * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    enabled_keys = [
        kid for kid in KEY_ORDER if settings["keys"].get(kid, {}).get("enabled")
    ] or ["num", "caps"]

    if len(enabled_keys) == 1:
        kid = enabled_keys[0]
        return tray_image(
            kid,
            states.get(kid, False),
            settings["keys"][kid],
            settings["tray"].get("style", "badge"),
            size_name,
        )

    pad = int(S * 0.06)
    gap = int(S * 0.06)
    cell = (S - 2 * pad - gap) // 2
    positions = [
        (pad, pad),
        (pad + cell + gap, pad),
        (pad, pad + cell + gap),
        (pad + cell + gap, pad + cell + gap),
    ]
    f = _load_font("bold", int(cell * 0.56))
    for idx, kid in enumerate(enabled_keys[:4]):
        x, y = positions[idx]
        on = states.get(kid, False)
        k = settings["keys"][kid]
        rgb = _hex_to_rgb(k.get("color_on", GREEN) if on else k.get("color_off", RED))
        d.rounded_rectangle(
            [x, y, x + cell, y + cell], radius=int(cell * 0.28), fill=rgb + (255,)
        )
        _draw_centered_text(
            d, (x, y, x + cell, y + cell), KEYS[kid]["badge"], f
        )

    return img.resize((px, px), Image.LANCZOS)


def png_dataurl(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def style_preview(kid, style, size=72, on=True, color=GREEN):
    img = _render_style(kid, on, color, style, size)
    return png_dataurl(img)


def render_osd(key_id, on, key_settings, scale=1.0, lang=None):
    """Render the glassmorphic OSD notification pill using Vazirmatn."""
    lang = lang or strings.LANG
    scale = max(0.8, min(1.8, float(scale or 1.0)))

    w = int(280 * scale)
    h = int(68 * scale)
    ss = 2
    W, H = w * ss, h * ss

    bg_key = TRANSPARENT_RGB + (255,) if IS_WINDOWS else (11, 15, 23, 255)
    img = Image.new("RGBA", (W, H), bg_key)
    d = ImageDraw.Draw(img)

    pad = int(4 * scale * ss)
    rad = int(20 * scale * ss)
    color_hex = key_settings.get("color_on", GREEN) if on else key_settings.get("color_off", RED)
    accent = _hex_to_rgb(color_hex, (34, 197, 94) if on else (239, 68, 68))

    # Pill body & border
    d.rounded_rectangle(
        [pad, pad, W - pad, H - pad],
        radius=rad,
        fill=(16, 22, 33, 255),
        outline=accent + (180,),
        width=max(2, int(1.8 * scale * ss)),
    )

    # Keycap badge
    cap_size = int(42 * scale * ss)
    cap_y = (H - cap_size) // 2
    if lang == "fa":
        cap_x = W - pad - int(14 * scale * ss) - cap_size
    else:
        cap_x = pad + int(14 * scale * ss)

    d.rounded_rectangle(
        [cap_x, cap_y, cap_x + cap_size, cap_y + cap_size],
        radius=int(12 * scale * ss),
        fill=accent + (255,),
    )
    f_cap = _load_font("bold", int(14 * scale * ss))
    _draw_centered_text(
        d,
        (cap_x, cap_y, cap_x + cap_size, cap_y + cap_size),
        KEYS.get(key_id, KEYS["num"])["keycap"],
        f_cap,
    )

    # Status text (shaped with Vazirmatn)
    kname = strings.key_name(key_id, lang)
    raw_msg = strings.tr("osd_turned_on" if on else "osd_turned_off", lang).format(kname)
    msg = _prep_text(raw_msg)
    f_msg = _load_font("bold", int(15 * scale * ss))

    if lang == "fa":
        tx_box = (pad + int(18 * scale * ss), pad, cap_x - int(12 * scale * ss), H - pad)
    else:
        tx_box = (cap_x + cap_size + int(12 * scale * ss), pad, W - pad - int(18 * scale * ss), H - pad)

    _draw_centered_text(d, tx_box, msg, f_msg, fill=(235, 242, 255, 255))

    out = img.resize((w, h), Image.NEAREST if IS_WINDOWS else Image.LANCZOS)
    return out, (w, h)