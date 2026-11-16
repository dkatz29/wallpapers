#!/usr/bin/env python3
"""Matched light + dark abstract wallpapers for the iPhone Duo inner display (1878 x 2670).

Look: Apple-inspired - soft dimensional forms, folded ribbons, frosted glass panes,
gentle blooms of light, calm top third for the lock-screen clock.
Palette: only blue, teal, tan, khaki, grey.

Outputs (in --out):  light.png  dark.png  manifest.json
Usage: python3 generate_wallpapers.py --out ./latest [--date 2026-11-17] [--style ribbons|bloom|glass|dunes]
"""
import argparse, colorsys, datetime as dt, hashlib, json, os
import numpy as np
from PIL import Image, ImageFilter

W, H = 1878, 2670
STYLES = ["ribbons", "bloom", "glass", "dunes"]

# hue (deg), saturation for each allowed family
FAMILIES = {
    "blue":  (213, 0.55),
    "teal":  (184, 0.45),
    "tan":   (33,  0.32),
    "khaki": (52,  0.26),
    "grey":  (210, 0.06),
}
# curated pairings so every day reads as one considered palette
COMBOS = [
    ["grey", "blue", "teal"], ["tan", "khaki", "grey"], ["teal", "tan", "grey"],
    ["blue", "khaki", "grey"], ["blue", "teal", "tan"], ["khaki", "teal", "grey"],
    ["grey", "tan", "blue"],
]


def hls(fam, l, rng, ds=0.0):
    h, s = FAMILIES[fam]
    h = (h + rng.uniform(-4, 4)) % 360
    return np.array(colorsys.hls_to_rgb(h / 360, l, np.clip(s + ds, 0, 1)), np.float32)


def palette(combo, mode, seed):
    """bg (top/bottom) + 3 accent tones per family. Same seed -> same hues in both modes."""
    rng = np.random.default_rng(seed)
    if mode == "light":
        bg_top, bg_bot = hls(combo[0], 0.95, rng, -0.1), hls(combo[0], 0.88, rng)
        acc = [(hls(f, 0.80, rng), hls(f, 0.68, rng), hls(f, 0.90, rng)) for f in combo]
    else:
        bg_top, bg_bot = hls(combo[0], 0.06, rng, -0.1), hls(combo[0], 0.11, rng)
        warm = lambda f: -0.1 if f in ("tan", "khaki") else 0.0   # keep tan/khaki from going brown
        acc = [(hls(f, 0.27, rng, warm(f)), hls(f, 0.16, rng, warm(f)), hls(f, 0.42, rng, warm(f))) for f in combo]
    return bg_top, bg_bot, acc  # acc[i] = (mid, shadow, highlight)


Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
X /= H; Y /= H          # height-normalised coords; width = 0.703
AR = W / H


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def background(top, bot):
    t = smooth(0, 1, Y)[..., None]
    return top * (1 - t) + bot * t


def over(img, col, a):
    a = a[..., None] if a.ndim == 2 else a
    return img * (1 - a) + col * a


def soft_shadow(img, mask, mode, strength):
    sh = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(H * 0.018)), np.float32) / 255
    off = int(H * 0.012)                       # light from above: shift down, no wrap
    sh = np.concatenate([np.zeros((off, W), np.float32), sh[:-off]], axis=0)
    k = strength * (0.55 if mode == "dark" else 1.0)
    return img * (1 - k * sh * (1 - mask))[..., None]


# ---------- styles ----------

def ribbons(pal, rng, mode):
    """Folded, satin-like ribbons sweeping diagonally, cylinder-shaded."""
    top, bot, acc = pal
    img = background(top, bot)
    ang = rng.uniform(-0.55, -0.25)
    u = X * np.cos(ang) - Y * np.sin(ang)
    v = X * np.sin(ang) + Y * np.cos(ang)
    n = int(rng.integers(3, 5))
    for i in range(n):
        mid, shadow, hi = acc[i % len(acc)]
        c = 0.42 + i * rng.uniform(0.11, 0.16) + rng.uniform(-0.03, 0.03)
        centre = c + 0.07 * np.sin(u * rng.uniform(2.2, 3.6) + rng.uniform(0, 6.3)) \
                   + 0.025 * np.sin(u * rng.uniform(5, 7) + rng.uniform(0, 6.3))
        thick = rng.uniform(0.07, 0.12) * (1 + 0.35 * np.sin(u * rng.uniform(1.5, 3) + rng.uniform(0, 6.3)))
        d = (v - centre) / thick                       # -1..1 across the ribbon
        mask = smooth(1.0, 0.985, np.abs(d))
        img = soft_shadow(img, mask, mode, 0.28)
        light = np.clip(1 - d, 0, 2) / 2               # brighter on upper edge
        col = shadow[None, None] * (1 - light[..., None]) + mid[None, None] * light[..., None]
        sheen = np.exp(-((d + 0.45) / 0.18) ** 2)      # satin highlight
        col = col * (1 - 0.6 * sheen[..., None]) + hi * 0.6 * sheen[..., None]
        img = over(img, col, mask)
    return img


def bloom(pal, rng, mode):
    """Soft orbs of coloured light drifting in a calm field (macOS / iOS 17 feel)."""
    top, bot, acc = pal
    img = background(top, bot)
    for i in range(int(rng.integers(5, 8))):
        mid, shadow, hi = acc[i % len(acc)]
        cx, cy = rng.uniform(-0.1, AR + 0.1), rng.uniform(0.38, 1.05)
        rx, ry = rng.uniform(0.18, 0.42), rng.uniform(0.15, 0.35)
        g = np.exp(-(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2) * 1.4)
        tone = (hi if i % 3 == 0 else mid) if mode == "dark" else (shadow if i % 2 else mid)
        img = over(img, tone, g * rng.uniform(0.75, 1.0))
    return img


def rrect_sdf(px, py, cx, cy, hw, hh, r, a):
    x = (px - cx) * np.cos(a) + (py - cy) * np.sin(a)
    y = -(px - cx) * np.sin(a) + (py - cy) * np.cos(a)
    qx, qy = np.abs(x) - hw + r, np.abs(y) - hh + r
    return np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - r


def glass(pal, rng, mode):
    """Stacked frosted-glass panes over a bloom field (Liquid Glass)."""
    img = bloom(pal, rng, mode)
    _, _, acc = pal
    a0 = rng.uniform(-0.5, 0.5)
    for i in range(int(rng.integers(3, 5))):
        mid, shadow, hi = acc[i % len(acc)]
        cx, cy = rng.uniform(0.15, AR - 0.15), rng.uniform(0.5, 0.92)
        hw, hh = rng.uniform(0.16, 0.28), rng.uniform(0.10, 0.20)
        sdf = rrect_sdf(X, Y, cx, cy, hw, hh, min(hw, hh) * 0.55, a0 + rng.uniform(-0.25, 0.25))
        mask = smooth(0.0015, -0.0015, sdf)
        img = soft_shadow(img, mask, mode, 0.22)
        frost = img * 0.55 + (hi if mode == "light" else mid) * 0.45
        rim = np.exp(-(sdf / 0.0022) ** 2) * (0.9 if mode == "dark" else 0.7)
        inner_glow = smooth(-0.06, 0.0, sdf) * 0.25
        img = over(img, frost, mask)
        img = over(img, np.array([1, 1, 1], np.float32), (rim + inner_glow * mask) * (0.55 if mode == "light" else 0.18))
    return img


def dunes(pal, rng, mode):
    """Layered, softly lit horizons - calm sky, sculpted foreground."""
    top, bot, acc = pal
    img = background(top, bot)
    n = 5
    for i in range(n):
        mid, shadow, hi = acc[(i + 1) % len(acc)]
        base = 0.50 + 0.5 * i / n
        edge = base + 0.05 * np.sin(X * rng.uniform(3, 5) + rng.uniform(0, 6.3)) \
                    + 0.02 * np.sin(X * rng.uniform(7, 10) + rng.uniform(0, 6.3))
        mask = smooth(-0.0015, 0.0015, Y - edge)
        img = soft_shadow(img, mask, mode, 0.3)
        depth = smooth(0, 0.25, Y - edge)[..., None]
        col = hi * (1 - depth) * 0.35 + mid * (0.65 + 0.35 * depth) * (1 - depth * 0.2) + shadow * depth * 0.2
        img = over(img, col, mask)
    return img


def finish(arr, seed, mode):
    g = np.random.default_rng(seed).normal(0, 1.1 if mode == "dark" else 1.4, (H, W, 1))
    out = np.clip(arr * 255 + g, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--style", choices=STYLES)
    ap.add_argument("--combo", help="comma list from: " + ",".join(FAMILIES))
    a = ap.parse_args()

    seed = int(hashlib.sha256(a.date.encode()).hexdigest()[:8], 16)
    style = a.style or STYLES[seed % len(STYLES)]
    combo = a.combo.split(",") if a.combo else COMBOS[(seed // 7) % len(COMBOS)]
    assert all(c in FAMILIES for c in combo), "colours limited to " + ", ".join(FAMILIES)
    os.makedirs(a.out, exist_ok=True)
    manifest = {"date": a.date, "seed": seed, "style": style, "colors": combo, "size": [W, H], "files": []}

    for mode in ("light", "dark"):
        pal = palette(combo, mode, seed + 1)
        arr = globals()[style](pal, np.random.default_rng(seed + 99), mode)
        fn = f"{mode}.png"
        finish(arr, seed + len(mode), mode).save(os.path.join(a.out, fn), optimize=True)
        manifest["files"].append(fn)

    with open(os.path.join(a.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
