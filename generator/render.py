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

# iPhone Duo inner folding display. The outer display lines up with it.
WIDTH, HEIGHT = 1878, 2670
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

STYLES = ("waves", "arcs", "orbs", "capsules", "dunes", "tiers")


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
    top, bottom = p.get("top", 0.30), p.get("bottom", 0.88)
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
    cy = {"t": -0.12, "b": 1.12}[corner[0]] + rng.uniform(-0.06, 0.06)
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
        cands = [(rng.uniform(0.0, 1.0), rng.uniform(0.08, 0.95)) for _ in range(12)]
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
    cx0, cy0 = _sx(0.5), _sy(0.5)
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
    top, bottom = p.get("top", 0.22), p.get("bottom", 0.86)
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
    top, bottom = p.get("top", 0.28), p.get("bottom", 0.84)
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


GEOMETRY = {
    "waves": geom_waves, "arcs": geom_arcs, "orbs": geom_orbs,
    "capsules": geom_capsules, "dunes": geom_dunes, "tiers": geom_tiers,
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
    opacity = float(params.get("opacity", 1.0))
    for (kind, geom), color in zip(shapes, v["layers"]):
        mask = Image.new("L", size, 0)
        d = ImageDraw.Draw(mask)
        fill = int(255 * max(0.0, min(1.0, opacity)))
        if kind == "poly":
            d.polygon(geom, fill=fill)
        else:
            d.ellipse(geom, fill=fill)
        img.paste(Image.new("RGB", size, _rgb(color)), (0, 0), mask)
    return img.resize((WIDTH, HEIGHT), Image.LANCZOS)


def render(spec: dict) -> dict[str, Image.Image]:
    validate(spec)
    rng = random.Random(int(spec["seed"]))
    n = len(spec["light"]["layers"])
    shapes = GEOMETRY[spec["style"]](n, rng, spec.get("params", {}))
    return {mode: render_variant(spec, mode, shapes) for mode in ("light", "dark")}


def preview(images: dict[str, Image.Image]) -> Image.Image:
    scale = 0.25
    w, h = int(WIDTH * scale), int(HEIGHT * scale)
    pad = 24
    sheet = Image.new("RGB", (w * 2 + pad * 3, h + pad * 2), (128, 132, 138))
    for i, mode in enumerate(("light", "dark")):
        sheet.paste(images[mode].resize((w, h), Image.LANCZOS), (pad + i * (w + pad), pad))
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
