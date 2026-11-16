#!/usr/bin/env python3
"""Render a light + dark wallpaper pair for the iPhone Duo inner display.

Claude writes a design spec (specs/YYYY-MM-DD.json); this script turns it into
pixels. Geometry is shared between the light and dark variants so the sunrise /
sunset swap feels like the same wallpaper changing its lighting, not a new image.

Usage:
    python generator/render.py specs/2026-11-17.json            # render + publish to latest/
    python generator/render.py specs/2026-11-17.json --out tmp/  # render somewhere else
    python generator/render.py --palette                         # list allowed colors
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

# iPhone Duo inner folding display, in portrait. The outer display shows nearly
# the same view (it trims ~2% off each side).
WIDTH, HEIGHT = 1878, 2670
# iOS builds the inner display's LANDSCAPE wallpaper from the portrait crop: it
# scales the image to the landscape width, so only a band about half the height
# is visible, starting ~8% from the top (measured with a calibration image on
# 2026-11-16). Designs must work as a whole in portrait AND within this band.
LANDSCAPE_ASPECT = 2670 / 1878
LANDSCAPE_TOP = 0.08
LANDSCAPE_BOTTOM = LANDSCAPE_TOP + (WIDTH / LANDSCAPE_ASPECT) / HEIGHT  # ~0.575
SUPERSAMPLE = 2  # draw at 2x, downscale with Lanczos for clean anti-aliased edges

REPO = Path(__file__).resolve().parent.parent

# The ONLY colors a wallpaper may use: blues, teals, tans, khakis, greys.
# Grouped by tone so the skill can follow simple light/dark rules.
PALETTE: dict[str, dict[str, str]] = {
    "light": {
        "linen": "#F2EDE4",     # tan
        "sand": "#E4D8C3",      # tan
        "parchment": "#EAE3D2", # tan
        "fog": "#E6E8EA",       # grey
        "cloud": "#D5D9DD",     # grey
        "mist": "#CFE0E6",      # blue-grey
        "ice": "#DCEAF0",       # pale blue
        "seafoam": "#B5DAD3",   # pale teal
    },
    "mid": {
        "khaki": "#C9BC97",
        "dune": "#A8946C",      # deep khaki / tan
        "stone": "#B9BDC2",     # grey
        "slate": "#6B737D",     # grey
        "sky": "#9CC3DE",       # blue
        "cornflower": "#6F9DC8",# blue
        "ocean": "#2F6E9E",     # blue
        "lagoon": "#5BA8A6",    # teal
        "teal": "#3E8E8A",      # teal
    },
    "dark": {
        "deep_teal": "#1D4F52",
        "harbor": "#24434F",    # blue-teal
        "navy": "#1B2E45",
        "midnight": "#0F1A26",
        "graphite": "#24282D",
        "ink": "#12161B",
        "olive_khaki": "#5C5640",
        "umber": "#3E382C",     # dark tan
    },
}
COLORS = {name: hexv for tone in PALETTE.values() for name, hexv in tone.items()}
TONE_OF = {name: tone for tone, group in PALETTE.items() for name in group}

STYLES = ("waves", "arcs", "orbs", "capsules", "dunes", "tiers",
          "petals", "bauhaus", "squircles", "folds", "horizon", "ribbons", "blobs", "topo")


# ---------------------------------------------------------------- validation

class SpecError(ValueError):
    pass


def validate(spec: dict) -> None:
    for key in ("date", "title", "seed", "style", "light", "dark"):
        if key not in spec:
            raise SpecError(f"spec is missing '{key}'")
    if spec["style"] not in STYLES:
        raise SpecError(f"style must be one of {STYLES}")
    for mode in ("light", "dark"):
        v = spec[mode]
        bg, layers = v.get("background"), v.get("layers")
        if not isinstance(bg, list) or not 1 <= len(bg) <= 2:
            raise SpecError(f"{mode}.background must be a list of 1-2 color names")
        if not isinstance(layers, list) or not 2 <= len(layers) <= 8:
            raise SpecError(f"{mode}.layers must be a list of 2-8 color names")
        for c in bg + layers:
            if c not in COLORS:
                raise SpecError(f"'{c}' is not in the palette (run --palette)")
        if mode == "light" and any(TONE_OF[c] == "dark" for c in bg):
            raise SpecError("light background must use light or mid tones")
        if mode == "dark" and any(TONE_OF[c] != "dark" for c in bg):
            raise SpecError("dark background must use dark tones only")
    if len(spec["light"]["layers"]) != len(spec["dark"]["layers"]):
        raise SpecError("light.layers and dark.layers must have the same length")


# ---------------------------------------------------------------- geometry
# Every shape is a polygon (or ellipse) in pixel space at supersampled size.
# Layers are listed back-to-front.

def _sx(x: float) -> float:
    return x * WIDTH * SUPERSAMPLE


def _sy(y: float) -> float:
    return y * HEIGHT * SUPERSAMPLE


def geom_waves(n, rng, p):
    amp = p.get("amplitude", 0.035)
    top, bottom = p.get("top", 0.24), p.get("bottom", 0.74)
    shapes = []
    for i in range(n):
        base = top + (bottom - top) * i / max(1, n - 1)
        f1, f2 = rng.uniform(0.5, 1.3), rng.uniform(1.4, 2.6)
        p1, p2 = rng.random(), rng.random()
        a1, a2 = amp * rng.uniform(0.7, 1.2), amp * rng.uniform(0.2, 0.45)
        pts = []
        for k in range(181):
            x = -0.02 + 1.04 * k / 180
            y = base + a1 * math.sin(2 * math.pi * (f1 * x + p1)) + a2 * math.sin(2 * math.pi * (f2 * x + p2))
            pts.append((_sx(x), _sy(y)))
        pts += [(_sx(1.02), _sy(1.02)), (_sx(-0.02), _sy(1.02))]
        shapes.append(("poly", pts))
    return shapes


def geom_arcs(n, rng, p):
    corner = p.get("corner") or rng.choice(["bl", "br", "tl", "tr"])
    cx = {"l": -0.25, "r": 1.25}[corner[1]] + rng.uniform(-0.1, 0.1)
    # Bottom corners sit at ~0.8 so the rings reach into the landscape band (y <= 0.575).
    cy = {"t": -0.12, "b": 0.8}[corner[0]] + rng.uniform(-0.06, 0.06)
    r_max, r_min = p.get("r_max", 1.25), p.get("r_min", 0.35)
    shapes = []
    for i in range(n):
        r = r_max - (r_max - r_min) * i / max(1, n - 1)
        rx, ry = _sx(r), _sx(r)  # circles: radius measured in widths
        x0, y0 = _sx(cx), _sy(cy)
        shapes.append(("ellipse", (x0 - rx, y0 - ry, x0 + rx, y0 + ry)))
    return shapes


def geom_orbs(n, rng, p):
    shapes = []
    radii = sorted((rng.uniform(p.get("r_min", 0.22), p.get("r_max", 0.62)) for _ in range(n)), reverse=True)
    placed: list[tuple[float, float]] = []
    aspect = HEIGHT / WIDTH
    for r in radii:
        # Best-candidate sampling: keep orbs spread out instead of stacking into a bullseye.
        cands = [(rng.uniform(0.0, 1.0), rng.uniform(0.12, 0.7)) for _ in range(12)]
        cx, cy = max(cands, key=lambda c: min(
            (math.hypot(c[0] - px, (c[1] - py) * aspect) for px, py in placed), default=0))
        placed.append((cx, cy))
        rx = _sx(r)
        x0, y0 = _sx(cx), _sy(cy)
        shapes.append(("ellipse", (x0 - rx, y0 - rx, x0 + rx, y0 + rx)))
    return shapes


def _capsule(cx, cy, length, thick, angle_deg):
    """Pill shape as a polygon, centre/size in pixels."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)       # along the pill
    nx, ny = -uy, ux                        # across the pill
    half, r = length / 2 - thick / 2, thick / 2
    pts = []
    for end, sign in ((1, 1), (-1, -1)):
        ex, ey = cx + ux * half * end, cy + uy * half * end
        for k in range(41):
            t = -math.pi / 2 + math.pi * k / 40
            dx = math.cos(t) * sign
            dy = math.sin(t) * sign
            pts.append((ex + (ux * dx + nx * dy) * r, ey + (uy * dx + ny * dy) * r))
    return pts


def geom_capsules(n, rng, p):
    angle = p.get("angle", rng.choice([-35, -30, 30, 35, 55, -55]))
    thick = _sx(p.get("thickness", 0.30))
    gap = thick * p.get("spacing", 0.82)
    a = math.radians(angle)
    nx, ny = -math.sin(a), math.cos(a)
    ux, uy = math.cos(a), math.sin(a)
    cx0, cy0 = _sx(0.5), _sy(0.42)
    shapes = []
    for i in range(n):
        off = (i - (n - 1) / 2) * gap
        slide = rng.uniform(-0.35, 0.35) * _sx(1)
        cx = cx0 + nx * off + ux * slide
        cy = cy0 + ny * off + uy * slide
        length = _sy(rng.uniform(0.75, 1.15))
        shapes.append(("poly", _capsule(cx, cy, length, thick, angle)))
    return shapes


def _bezier(p0, p1, p2, p3, steps=160):
    out = []
    for k in range(steps + 1):
        t = k / steps
        mt = 1 - t
        out.append((
            mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0],
            mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1],
        ))
    return out


def geom_dunes(n, rng, p):
    tilt = p.get("tilt", rng.choice([-0.18, -0.12, 0.12, 0.18]))
    top, bottom = p.get("top", 0.2), p.get("bottom", 0.72)
    shapes = []
    for i in range(n):
        base = top + (bottom - top) * i / max(1, n - 1)
        yl, yr = base - tilt / 2, base + tilt / 2
        c1 = (rng.uniform(0.2, 0.45), base + rng.uniform(-0.16, 0.06))
        c2 = (rng.uniform(0.55, 0.8), base + rng.uniform(-0.06, 0.16))
        curve = _bezier((-0.02, yl), c1, c2, (1.02, yr))
        pts = [(_sx(x), _sy(y)) for x, y in curve]
        pts += [(_sx(1.02), _sy(1.05)), (_sx(-0.02), _sy(1.05))]
        shapes.append(("poly", pts))
    return shapes


def geom_tiers(n, rng, p):
    """Stacked rounded plateaus — flat, architectural, a little like terraced hills."""
    top, bottom = p.get("top", 0.24), p.get("bottom", 0.72)
    shapes = []
    for i in range(n):
        base = top + (bottom - top) * i / max(1, n - 1)
        rise = rng.uniform(0.04, 0.10)
        x_mid = rng.uniform(0.25, 0.75)
        width = rng.uniform(0.35, 0.7)
        xl, xr = x_mid - width / 2, x_mid + width / 2
        left = _bezier((-0.02, base), (xl - 0.12, base), (xl - 0.05, base - rise), (xl + 0.08, base - rise), 60)
        right = _bezier((xr - 0.08, base - rise), (xr + 0.05, base - rise), (xr + 0.12, base), (1.02, base), 60)
        pts = [(_sx(x), _sy(y)) for x, y in left + right]
        pts += [(_sx(1.02), _sy(1.05)), (_sx(-0.02), _sy(1.05))]
        shapes.append(("poly", pts))
    return shapes


# ---- shapes that may reuse a layer colour: these return (kind, geom, colour_index)

ASPECT = HEIGHT / WIDTH


def _rot(x, y, ang):
    c, s = math.cos(ang), math.sin(ang)
    return x * c - y * s, x * s + y * c


def geom_petals(n, rng, p):
    """Leaf shapes fanning from a point: a flat flower, iris or sunburst."""
    mode = p.get("mode", rng.choice(["flower", "fan"]))
    if mode == "fan":  # rising from the bottom edge
        cx, cy = p.get("cx", rng.uniform(0.3, 0.7)), p.get("cy", rng.uniform(0.62, 0.7))
        spread, start = p.get("spread", rng.uniform(120, 170)), None
    else:
        cx, cy = p.get("cx", rng.uniform(0.35, 0.65)), p.get("cy", rng.uniform(0.4, 0.5))
        spread, start = 360, rng.uniform(0, 360)
    count = int(p.get("count", rng.choice([5, 6, 7, 8, 9, 10, 12])))
    length = _sx(p.get("length", rng.uniform(0.55, 0.85)))  # in screen widths
    half_w = _sx(p.get("width", rng.uniform(0.15, 0.26))) / 2
    pointed = p.get("tip", rng.choice(["pointed", "round"])) == "pointed"
    if start is None:
        start = -90 - spread / 2
    ox, oy = _sx(cx), _sy(cy)
    shapes = []
    for k in range(count):
        frac = k / count if spread >= 360 else k / max(1, count - 1)
        ang = math.radians(start + spread * frac)
        a = length / 2
        pts = []
        for j in range(96):
            t = 2 * math.pi * j / 96
            ex = a * math.cos(t)
            ey = half_w * math.sin(t) * (math.sqrt(1 - abs(math.cos(t))) if pointed else 1)
            rx, ry = _rot(ex + a, ey, ang)
            pts.append((ox + rx, oy + ry))
        shapes.append(("poly", pts, k % n))
    return shapes


def geom_bauhaus(n, rng, p):
    """Grid of square tiles with quarter circles, half circles and dots (mid-century)."""
    cols = int(p.get("cols", rng.choice([3, 4, 4, 5])))
    top = p.get("top", 0.22)
    cell_w = 1.0 / cols
    cell_h = cell_w / ASPECT
    rows = max(1, int((1 - top) / cell_h))
    y0 = 1 - rows * cell_h
    weights = p.get("mix", {"quarter": 3, "half": 2, "circle": 1, "none": 1})
    kinds = [k for k, w in weights.items() for _ in range(int(w))]
    shapes = []
    for r in range(rows):
        for c in range(cols):
            bx0, by0 = _sx(c * cell_w), _sy(y0 + r * cell_h)
            s = _sx(cell_w)
            bx1, by1 = bx0 + s, by0 + s
            tile = rng.randrange(n)
            shapes.append(("poly", [(bx0, by0), (bx1 + 1, by0), (bx1 + 1, by1 + 1), (bx0, by1 + 1)], tile))
            fg = rng.choice([i for i in range(n) if i != tile])
            kind = rng.choice(kinds)
            if kind == "quarter":
                corner = rng.randrange(4)  # 0 TL, 1 TR, 2 BR, 3 BL; pie sweeps into the cell
                px = bx0 if corner in (0, 3) else bx1
                py = by0 if corner in (0, 1) else by1
                st = 90 * corner
                shapes.append(("pie", ((px - s, py - s, px + s, py + s), st, st + 90), fg))
            elif kind == "half":
                side = rng.randrange(4)  # 0 top, 1 right, 2 bottom, 3 left edge
                mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
                px, py, st = [(mx, by0, 0), (bx1, my, 90), (mx, by1, 180), (bx0, my, 270)][side]
                h = s / 2
                shapes.append(("pie", ((px - h, py - h, px + h, py + h), st, st + 180), fg))
            elif kind == "circle":
                rr = s * rng.choice([0.28, 0.36, 0.42])
                mx, my = (bx0 + bx1) / 2, (by0 + by1) / 2
                shapes.append(("ellipse", (mx - rr, my - rr, mx + rr, my + rr), fg))
    return shapes


def _superellipse(cx, cy, rx, ry, e, rot, steps=240):
    pts = []
    for j in range(steps):
        t = 2 * math.pi * j / steps
        c, s = math.cos(t), math.sin(t)
        x = rx * math.copysign(abs(c) ** (2 / e), c)
        y = ry * math.copysign(abs(s) ** (2 / e), s)
        x, y = _rot(x, y, rot)
        pts.append((cx + x, cy + y))
    return pts


def geom_squircles(n, rng, p):
    """Nested Apple-icon squircles drifting off-centre."""
    e = p.get("exponent", rng.choice([4.0, 5.0, 6.0]))
    r_max, r_min = p.get("r_max", 0.95), p.get("r_min", 0.16)  # half-size in widths
    cx, cy = p.get("cx", rng.uniform(0.35, 0.65)), p.get("cy", rng.uniform(0.4, 0.5))
    dx, dy = rng.uniform(-0.05, 0.05), rng.uniform(-0.035, 0.035)
    rot = math.radians(p.get("rotation", rng.choice([0, 0, 10, -10, 22, -22, 45])))
    shapes = []
    for i in range(n):
        r = r_max - (r_max - r_min) * i / max(1, n - 1)
        shapes.append(("poly", _superellipse(_sx(cx + dx * i), _sy(cy + dy * i), _sx(r), _sx(r), e, rot), i))
    return shapes


def geom_folds(n, rng, p):
    """Folded-paper facets: straight creases with a kink or two, layered down the screen."""
    tilt = p.get("tilt", rng.choice([0.0, 0.0, -0.14, 0.14]))
    top, bottom = p.get("top", 0.22), p.get("bottom", 0.74)
    shapes = []
    for i in range(n):
        base = top + (bottom - top) * i / max(1, n - 1)
        kinks = sorted(rng.uniform(0.15, 0.85) for _ in range(rng.choice([1, 1, 2])))
        xs = [-0.02] + kinks + [1.02]
        pts = []
        for x in xs:
            y = base + tilt * (x - 0.5) + (rng.uniform(-0.08, 0.08) if 0 < x < 1 else rng.uniform(-0.04, 0.04))
            pts.append((_sx(x), _sy(y)))
        pts += [(_sx(1.02), _sy(1.05)), (_sx(-0.02), _sy(1.05))]
        shapes.append(("poly", pts, i))
    return shapes


def geom_horizon(n, rng, p):
    """A sun/moon disc (first layer colour) sinking behind flat horizon bands."""
    horizon = p.get("horizon", rng.uniform(0.42, 0.52))
    sun_r = p.get("sun_r", rng.uniform(0.17, 0.3))  # in widths
    sun_x = p.get("sun_x", rng.uniform(0.28, 0.72))
    sun_y = horizon - (sun_r / ASPECT) * p.get("sun_rise", rng.uniform(0.1, 0.75))
    sx, sy, sr = _sx(sun_x), _sy(sun_y), _sx(sun_r)
    shapes = [("ellipse", (sx - sr, sy - sr, sx + sr, sy + sr), 0)]
    bands = max(1, n - 1)
    curve = p.get("curve", rng.choice([0.0, 0.03, 0.05]))
    for i in range(bands):
        base = horizon + (0.97 - horizon) * (i / bands) ** 1.15
        c1 = (rng.uniform(0.2, 0.4), base + rng.uniform(-curve, curve))
        c2 = (rng.uniform(0.6, 0.8), base + rng.uniform(-curve, curve))
        pts = [(_sx(x), _sy(y)) for x, y in _bezier((-0.02, base + rng.uniform(-0.02, 0.02)), c1, c2,
                                                       (1.02, base + rng.uniform(-0.02, 0.02)), 90)]
        pts += [(_sx(1.02), _sy(1.05)), (_sx(-0.02), _sy(1.05))]
        shapes.append(("poly", pts, 1 + i if n > 1 else 0))
    return shapes


def geom_ribbons(n, rng, p):
    """Wide flat ribbons flowing down the screen with rounded heads."""
    half = _sx(p.get("width", rng.uniform(0.2, 0.3))) / 2
    amp = p.get("amplitude", rng.uniform(0.06, 0.16))  # in widths
    freq = p.get("frequency", rng.uniform(0.45, 1.0))  # cycles per screen height
    ang = math.radians(p.get("angle", rng.choice([0, 0, 12, -12, 22, -22])))
    head = p.get("top", rng.choice([-0.2, 0.15, 0.22]))  # where ribbons start (heights)
    phase0 = rng.random()
    shapes = []
    W2, H2 = _sx(1), _sy(1)
    for i in range(n):
        x0 = -0.1 + 1.2 * (i + 0.5) / n + rng.uniform(-0.015, 0.015)
        ph = phase0 + i * 0.03  # near-parallel so the ribbons flow together
        start = head + rng.uniform(0, 0.12) if head > 0 else head
        ys = [start + (1.3 - start) * k / 160 for k in range(161)]
        centre = []
        for y in ys:
            x = x0 + amp * math.sin(2 * math.pi * (freq * y + ph))
            px, py = _rot(_sx(x) - W2 / 2, _sy(y) - H2 / 2, ang)
            centre.append((px + W2 / 2, py + H2 / 2))
        left, right = [], []
        for k, (cx, cy) in enumerate(centre):
            ax, ay = centre[max(0, k - 1)]
            bx, by = centre[min(len(centre) - 1, k + 1)]
            tx, ty = bx - ax, by - ay
            norm = math.hypot(tx, ty) or 1
            nx, ny = -ty / norm, tx / norm
            left.append((cx + nx * half, cy + ny * half))
            right.append((cx - nx * half, cy - ny * half))
        # rounded head: semicircle from right[0] over the top to left[0]
        (cx, cy), (bx, by) = centre[0], centre[1]
        tx, ty = bx - cx, by - cy
        norm = math.hypot(tx, ty) or 1
        tx, ty = tx / norm, ty / norm
        rx, ry = right[0][0] - cx, right[0][1] - cy
        cap = []
        for j in range(1, 40):
            th = math.pi * j / 40
            cap.append((cx + math.cos(th) * rx - math.sin(th) * tx * half,
                        cy + math.cos(th) * ry - math.sin(th) * ty * half))
        shapes.append(("poly", right[::-1] + cap + left, i))
    return shapes


def _blob(cx, cy, r, harmonics, steps=200):
    pts = []
    for j in range(steps):
        t = 2 * math.pi * j / steps
        rr = r * (1 + sum(a * math.sin(k * t + ph) for k, a, ph in harmonics))
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return pts


def _harmonics(rng, wobble):
    return [(k, wobble * rng.uniform(0.4, 1.0) / k ** 0.9, rng.uniform(0, 2 * math.pi)) for k in (2, 3, 4, 5)]


def geom_blobs(n, rng, p):
    """Soft organic pebbles, spread out like orbs."""
    wobble = p.get("wobble", rng.uniform(0.12, 0.22))
    radii = sorted((rng.uniform(p.get("r_min", 0.2), p.get("r_max", 0.55)) for _ in range(n)), reverse=True)
    placed, shapes = [], []
    for i, r in enumerate(radii):
        cands = [(rng.uniform(0.0, 1.0), rng.uniform(0.2, 0.75)) for _ in range(12)]
        cx, cy = max(cands, key=lambda c: min(
            (math.hypot(c[0] - px, (c[1] - py) * ASPECT) for px, py in placed), default=0))
        placed.append((cx, cy))
        shapes.append(("poly", _blob(_sx(cx), _sy(cy), _sx(r), _harmonics(rng, wobble)), i))
    return shapes


def geom_topo(n, rng, p):
    """Nested organic rings, like a topographic map."""
    wobble = p.get("wobble", rng.uniform(0.1, 0.2))
    cx, cy = p.get("cx", rng.uniform(0.25, 0.75)), p.get("cy", rng.uniform(0.38, 0.5))
    r_max, r_min = p.get("r_max", 1.05), p.get("r_min", 0.12)
    base = _harmonics(rng, wobble)
    dx, dy = rng.uniform(-0.03, 0.03), rng.uniform(-0.02, 0.02)
    shapes = []
    for i in range(n):
        r = r_max - (r_max - r_min) * i / max(1, n - 1)
        harm = [(k, a * (1 + 0.15 * i), ph + 0.12 * i) for k, a, ph in base]
        shapes.append(("poly", _blob(_sx(cx + dx * i), _sy(cy + dy * i), _sx(r), harm), i))
    return shapes


GEOMETRY = {
    "waves": geom_waves, "arcs": geom_arcs, "orbs": geom_orbs,
    "capsules": geom_capsules, "dunes": geom_dunes, "tiers": geom_tiers,
    "petals": geom_petals, "bauhaus": geom_bauhaus, "squircles": geom_squircles,
    "folds": geom_folds, "horizon": geom_horizon, "ribbons": geom_ribbons,
    "blobs": geom_blobs, "topo": geom_topo,
}


# ---------------------------------------------------------------- rendering

def _rgb(name: str) -> tuple[int, int, int]:
    h = COLORS[name].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _background(colors: list[str], size, angle_deg: float) -> Image.Image:
    w, h = size
    if len(colors) == 1:
        return Image.new("RGB", size, _rgb(colors[0]))
    # Gentle linear gradient (Apple-style flat colour field, not a 3D effect).
    diag = int(math.hypot(w, h)) + 2
    grad = Image.linear_gradient("L").resize((diag, diag)).rotate(-angle_deg, resample=Image.BICUBIC)
    left, top = (diag - w) // 2, (diag - h) // 2
    mask = grad.crop((left, top, left + w, top + h))
    return Image.composite(Image.new("RGB", size, _rgb(colors[1])), Image.new("RGB", size, _rgb(colors[0])), mask)


def render_variant(spec: dict, mode: str, shapes) -> Image.Image:
    size = (WIDTH * SUPERSAMPLE, HEIGHT * SUPERSAMPLE)
    v = spec[mode]
    params = spec.get("params", {})
    img = _background(v["background"], size, params.get("gradient_angle", 0))
    opacity = max(0.0, min(1.0, float(params.get("opacity", 1.0))))

    def draw(d, kind, geom, fill):
        if kind == "poly":
            d.polygon(geom, fill=fill)
        elif kind == "ellipse":
            d.ellipse(geom, fill=fill)
        elif kind == "pie":
            bbox, start, end = geom
            d.pieslice(bbox, start, end, fill=fill)

    direct = ImageDraw.Draw(img)
    for kind, geom, ci in shapes:
        color = _rgb(v["layers"][ci % len(v["layers"])])
        if opacity >= 1.0:
            draw(direct, kind, geom, color)
        else:
            mask = Image.new("L", size, 0)
            draw(ImageDraw.Draw(mask), kind, geom, int(255 * opacity))
            img.paste(Image.new("RGB", size, color), (0, 0), mask)
            direct = ImageDraw.Draw(img)
    return img.resize((WIDTH, HEIGHT), Image.LANCZOS)


def render(spec: dict) -> dict[str, Image.Image]:
    validate(spec)
    rng = random.Random(int(spec["seed"]))
    n = len(spec["light"]["layers"])
    raw = GEOMETRY[spec["style"]](n, rng, spec.get("params", {}))
    # Older styles return (kind, geom) with one shape per layer; newer ones add a colour index.
    shapes = [s if len(s) == 3 else (s[0], s[1], i) for i, s in enumerate(raw)]
    return {mode: render_variant(spec, mode, shapes) for mode in ("light", "dark")}


def landscape_view(img: Image.Image) -> Image.Image:
    """What the inner display shows in landscape: a band of the portrait image,
    scaled up to 2670 x 1878."""
    top, bottom = int(LANDSCAPE_TOP * HEIGHT), int(LANDSCAPE_BOTTOM * HEIGHT)
    return img.crop((0, top, WIDTH, bottom)).resize((2670, 1878), Image.LANCZOS)


def preview(images: dict[str, Image.Image]) -> Image.Image:
    """Two rows (light, dark): the portrait view, then the inner landscape view."""
    scale = 0.2
    pw, ph = int(WIDTH * scale), int(HEIGHT * scale)
    lw, lh = int(2670 * scale), int(1878 * scale)
    pad = 24
    sheet = Image.new("RGB", (pw + lw + pad * 3, ph * 2 + pad * 3), (128, 132, 138))
    for row, mode in enumerate(("light", "dark")):
        y = pad + row * (ph + pad)
        sheet.paste(images[mode].resize((pw, ph), Image.LANCZOS), (pad, y))
        sheet.paste(landscape_view(images[mode]).resize((lw, lh), Image.LANCZOS),
                    (pad * 2 + pw, y + (ph - lh) // 2))
    return sheet


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?", help="path to a spec JSON file")
    ap.add_argument("--out", default=str(REPO / "latest"), help="output directory (default: latest/)")
    ap.add_argument("--palette", action="store_true", help="print the allowed palette and exit")
    args = ap.parse_args()

    if args.palette:
        print(json.dumps(PALETTE, indent=2))
        return 0
    if not args.spec:
        ap.error("spec is required")

    spec = json.loads(Path(args.spec).read_text())
    try:
        images = render(spec)
    except SpecError as e:
        print(f"Invalid spec: {e}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for mode, img in images.items():
        img.save(out / f"{mode}.png", optimize=True)
    preview(images).save(out / "preview.png", optimize=True)
    manifest = {
        "date": spec["date"],
        "title": spec["title"],
        "style": spec["style"],
        "spec": f"specs/{Path(args.spec).name}",
        "size": [WIDTH, HEIGHT],
        "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Rendered '{spec['title']}' ({spec['style']}) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
