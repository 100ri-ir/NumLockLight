# -*- coding: utf-8 -*-
"""Fetch / refresh all third-party free assets (fonts, icons, sounds).

All sources are free & redistributable:
  * Vazirmatn font  — SIL Open Font License 1.1 (rastikerdar/vazirmatn)
  * Lucide keyboard icon — MIT (lucide-icons), rasterized via Iconify API
  * Kenney interface sounds — CC0 1.0 (kenney.nl, via Calinou mirror)

Usage:  py -3 build\\Fetch_Assets.py
"""
import os
import shutil
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

UA = {"User-Agent": "Mozilla/5.0 (NumLockLight asset fetcher)"}


def fetch(urls, dest, min_size=1000):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) >= min_size:
        print("  [skip] %s" % os.path.basename(dest))
        return True
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if len(data) < min_size:
                continue
            with open(dest, "wb") as f:
                f.write(data)
            print("  [ ok ] %s  (%d KB)" % (os.path.basename(dest), len(data) // 1024))
            return True
        except Exception as e:
            print("  [fail] %s -> %s" % (url.split("/")[-1], e))
    return False


# --------------------------------------------------------------------------
def fetch_fonts():
    print("Fonts (Vazirmatn, SIL OFL):")
    base = "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/ttf"
    alt = "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf"
    ok = True
    for w in ("Regular", "Medium", "SemiBold", "Bold"):
        name = "Vazirmatn-%s.ttf" % w
        ok = fetch(["%s/%s" % (base, name), "%s/%s" % (alt, name)],
                   os.path.join(ASSETS, "fonts", name)) and ok
    # OFL license text
    fetch(["https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/OFL.txt"],
          os.path.join(ASSETS, "fonts", "OFL.txt"), min_size=200)
    return ok


# --------------------------------------------------------------------------
def fetch_icon_glyph():
    """Lucide 'keyboard' glyph (MIT) via Iconify SVG API, rasterized to PNG."""
    print("Icon glyph (Lucide keyboard, MIT):")
    dest = os.path.join(ASSETS, "icons", "lucide-keyboard.png")
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        print("  [skip] lucide-keyboard.png")
        return True
    url = "https://api.iconify.design/lucide/keyboard.svg?height=256"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            svg = r.read()
        import cairosvg  # dev dependency only for this script
        cairosvg.svg2png(bytestring=svg, write_to=dest,
                         output_width=256, output_height=256)
        print("  [ ok ] lucide-keyboard.png (256px)")
        return True
    except ImportError:
        print("  [warn] cairosvg not installed - trying Pillow-free fallback")
        # Fallback: rasterize via any available converter is not guaranteed;
        # regenerate with: pip install cairosvg
        return os.path.exists(dest)
    except Exception as e:
        print("  [fail] %s" % e)
        return os.path.exists(dest)


def build_app_ico():
    """Compose the multi-size app.ico from the keyboard glyph."""
    print("App icon (app.ico):")
    dest = os.path.join(ASSETS, "icons", "app.ico")
    if os.path.exists(dest) and os.path.getsize(dest) > 3000:
        print("  [skip] app.ico")
        return True
    glyph = os.path.join(ASSETS, "icons", "lucide-keyboard.png")
    if not os.path.exists(glyph):
        print("  [fail] glyph missing")
        return False
    try:
        from PIL import Image, ImageDraw, ImageFilter
        size = 256
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

        def gradient_rounded(size, top, bottom, radius):
            base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            grad = Image.new("RGBA", (size, size))
            gd = ImageDraw.Draw(grad)
            for y in range(size):
                t = y / (size - 1)
                c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,)
                gd.line([(0, y), (size, y)], fill=c)
            mask = Image.new("L", (size, size), 0)
            md = ImageDraw.Draw(mask)
            md.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
            base.paste(grad, (0, 0), mask)
            return base

        img = gradient_rounded(size, (34, 197, 94), (16, 122, 87), int(size * 0.22))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([size * 0.06, size * 0.06, size * 0.94, size * 0.94],
                            radius=size * 0.2, outline=(255, 255, 255, 60),
                            width=max(2, size // 96))
        gs = int(size * 0.56)
        glyph_im = Image.open(glyph).convert("RGBA").resize((gs, gs), Image.LANCZOS)
        img.alpha_composite(glyph_im, (int(size * 0.22), int(size * 0.30)))
        cx, cy, r = int(size * 0.78), int(size * 0.20), int(size * 0.095)
        led = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ld = ImageDraw.Draw(led)
        for i in range(4, 0, -1):
            ld.ellipse([cx - r - i * (size // 40), cy - r - i * (size // 40),
                        cx + r + i * (size // 40), cy + r + i * (size // 40)],
                       fill=(200, 255, 220, 60))
        ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(235, 255, 245, 255))
        ld.ellipse([cx - r // 2 - 1, cy - r // 2 - 1, cx + r // 4, cy + r // 4],
                   fill=(255, 255, 255, 255))
        ld.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2],
                   outline=(255, 255, 255, 160), width=max(2, size // 100))
        img.alpha_composite(led)

        img.save(os.path.join(ASSETS, "icons", "app-icon-preview.png"))
        img.save(dest, format="ICO",
                 sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print("  [ ok ] app.ico (multi-size)")
        return True
    except Exception as e:
        print("  [fail] %s" % e)
        return False


# --------------------------------------------------------------------------
def fetch_sounds():
    """Kenney Interface Sounds (CC0) — cloned from the Calinou GitHub mirror.

    A full clone is small (~1 MB); we pick the 8 effects we bundle.
    """
    print("Sounds (Kenney Interface Sounds, CC0):")
    snd_dir = os.path.join(ASSETS, "sounds")
    picked = {
        "confirmation_001.wav": "on-chime.wav",
        "glass_004.wav": "on-glass.wav",
        "maximize_004.wav": "on-rise.wav",
        "select_004.wav": "on-select.wav",
        "minimize_003.wav": "off-fall.wav",
        "toggle_002.wav": "off-tick.wav",
        "glass_001.wav": "off-soft.wav",
        "click_001.wav": "click.wav",
    }
    missing = [src for src, dst in picked.items()
               if not os.path.exists(os.path.join(snd_dir, dst))]
    if not missing:
        print("  [skip] all 8 sounds present")
        return True

    import tempfile
    try:
        import subprocess
        tmp = tempfile.mkdtemp(prefix="kenney_")
        print("  cloning CC0 pack (github.com/Calinou/kenney-interface-sounds)...")
        subprocess.run(["git", "clone", "--depth", "1", "--quiet",
                        "https://github.com/Calinou/kenney-interface-sounds.git", tmp],
                       check=True, timeout=180)
        src_dir = os.path.join(tmp, "addons", "kenney_interface_sounds")
        for src, dst in picked.items():
            s = os.path.join(src_dir, src)
            if os.path.exists(s):
                os.makedirs(snd_dir, exist_ok=True)
                shutil.copy(s, os.path.join(snd_dir, dst))
                print("  [ ok ] %s" % dst)
            else:
                print("  [warn] %s not in pack" % src)
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:
        print("  [fail] clone: %s" % e)
        print("  hint: install git, or download manually from kenney.nl (CC0)")
        return False

    # credits
    with open(os.path.join(snd_dir, "CREDITS.md"), "w", encoding="utf-8") as f:
        f.write(
            "# Sound credits\n\n"
            "Interface Sounds by Kenney — https://kenney.nl\n"
            "License: Creative Commons Zero (CC0 1.0) — public domain.\n"
            "Mirrored from: https://github.com/Calinou/kenney-interface-sounds\n")
    return all(os.path.exists(os.path.join(snd_dir, dst)) for dst in picked.values())


# --------------------------------------------------------------------------

def main():
    ok = True
    ok = fetch_fonts() and ok
    ok = fetch_icon_glyph() and ok
    ok = build_app_ico() and ok
    ok = fetch_sounds() and ok
    print()
    if ok:
        print("All assets ready.")
    else:
        print("Some assets FAILED - check messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
