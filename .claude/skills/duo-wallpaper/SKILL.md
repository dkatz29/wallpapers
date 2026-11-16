---
name: duo-wallpaper
description: Design and publish the day's abstract light + dark wallpaper pair for the iPhone Duo inner display (a 2670x2670 square that fills the 1878x2670 screen in portrait and landscape), then commit and push so the iOS Shortcut can pick it up at sunrise/sunset. Use when asked to generate, regenerate, or publish the daily Duo wallpaper, or when the midnight routine runs.
---

# Daily iPhone Duo wallpaper

You are the designer. `generator/render.py` is the paintbrush: you write a small JSON
spec, it draws the light and dark versions with identical geometry, writes them to
`latest/`, and the iOS Shortcut downloads them from GitHub.

## Design brief (non-negotiable)

- **Modern, flat, Apple-inspired.** Bold, simple colour fields, generous negative
  space, smooth curves, calm rhythm. Think the flat abstract wallpapers in recent iOS
  and macOS, not older glossy/3D/bevelled/skeuomorphic ones. No textures, no shadows,
  no text, no logos.
- **Colours: blues, teals, tans, khakis, greys only.** The renderer only accepts
  names from its palette (`python generator/render.py --palette`), so stick to those.
- **Don't use every colour family every day.** Each day, pick a subset of the five
  families: usually 2–4, occasionally just 1–2 for a quiet tonal day, and only
  now and then all 5. Light and dark versions use the same families. Change the mix from
  day to day (e.g. tan + khaki only; blue + grey; teal + tan + grey; all five).
  Families by palette name:
  - blue: `ice`, `mist`, `sky`, `cornflower`, `ocean`, `navy`, `midnight`
  - teal: `seafoam`, `lagoon`, `teal`, `deep_teal`, `harbor`
  - tan: `linen`, `parchment`, `sand`, `dune`, `umber`
  - khaki: `khaki`, `olive_khaki`
  - grey: `fog`, `cloud`, `stone`, `slate`, `graphite`, `ink`

  Neutral backgrounds (`linen`, `fog`, `ink`, `graphite`) don't count toward the
  family mix. Record the chosen families in the spec as `"families": [...]`.
- **One square image, 2670 × 2670, that works in portrait and landscape.** The inner
  display is 1878 × 2670 and rotates. Portrait shows the middle 1878 columns of the
  square and landscape shows the middle 1878 rows, so only the central
  1878 × 1878 area (about 0.15–0.85 on both axes) is always visible. Put the focal
  shapes there; the outer 15% on each side is fill that only one orientation sees.
  The outer display lines up with the portrait view, so don't make a separate image.
- **Coordinates:** positions (`cx`, `cy`, `top`, `horizon`, …) are fractions of the
  square canvas (0–1). Sizes (`r_*`, `length`, `width`, `thickness`, `sun_r`) are
  in *screen widths*, i.e. multiples of 1878 px.
- **Light version** (sunrise to sunset): background from `light` (optionally `mid`)
  tones, layers mostly `light`/`mid`, with one or two richer `mid` accents.
- **Dark version** (sunset to sunrise): background from `dark` tones only; layers
  mostly `dark` with at most one or two muted `mid` accents. Keep it low-glare. It
  should feel like the same wallpaper at night, not a different one.
- Keep the top ~30% of the canvas fairly quiet. The lock-screen clock sits at the
  top of each view, and the landscape view starts at y ≈ 0.15. Avoid high-contrast
  detail straight along the centre lines (x = 0.5 and y = 0.5), where the fold falls
  in one orientation or the other.

## Steps

1. `cd` to the repo root. Ensure Pillow is available: `pip install -q -r requirements.txt`.
2. Work out today's date **in America/Chicago**: `TZ=America/Chicago date +%F`. The
   routine runs at local midnight, so this is the day the wallpaper will be shown.
   If `specs/<date>.json` already exists, only regenerate when explicitly asked.
3. Look at the last 14 files in `specs/` and **rotate styles**: never use a style that
   appeared in the last 7 days, and prefer the styles used least recently (or never).
   There are 14 styles; use them all over time. Also don't repeat the previous day's
   `families` set. Vary the mood across the week: sandy/khaki days, oceanic blue days,
   grey/teal days, the occasional full-palette day.

   | Style | Look |
   |---|---|
   | `waves` | Stacked flowing horizontal bands |
   | `arcs` | Concentric quarter-rings from a corner |
   | `orbs` | Overlapping flat circles |
   | `capsules` | Diagonal pill-shaped bars |
   | `dunes` | Tilted smooth sand-dune layers |
   | `tiers` | Terraced plateaus |
   | `petals` | Leaf shapes fanning from a point: flower, iris or sunburst |
   | `bauhaus` | Tile grid of quarter circles, half circles and dots (mid-century) |
   | `squircles` | Nested Apple-icon rounded squares drifting off-centre |
   | `folds` | Folded-paper facets with straight creases |
   | `horizon` | Sun/moon disc (first layer colour) behind flat horizon bands |
   | `ribbons` | Wide flat ribbons flowing down the screen |
   | `blobs` | Soft organic pebble shapes |
   | `topo` | Nested organic rings, like a topographic map |

   Even within a style, push variety with `params` (angle, corner, mode, count, scale)
   so two `petals` days don't look alike.
4. Write `specs/<date>.json`:

   ```json
   {
     "date": "2026-11-17",
     "title": "Two-word evocative name",
     "seed": 48213,
     "style": "one of the 14 styles above",
     "families": ["blue", "teal"],
     "params": {},
     "light": { "background": ["fog", "ice"], "layers": ["mist", "sky", "lagoon", "teal"] },
     "dark":  { "background": ["midnight", "navy"], "layers": ["harbor", "deep_teal", "teal", "ocean"] },
     "notes": "One sentence on the idea."
   }
   ```

   - `background`: 1 colour (solid) or 2 (gentle gradient).
   - `layers`: 2–8 colours, back to front. Light and dark lists **must be the same length**
     (same shapes, different colours). 3–6 layers usually looks best.
   - `seed`: any new integer. It drives the geometry.
   - Optional `params` (all optional, sensible defaults):
     - all: `gradient_angle` (degrees, background gradient), `opacity` (0–1, default 1)
     - `waves`: `amplitude` (0.02–0.06), `top`, `bottom` (0–1 band range)
     - `arcs`: `corner` (`bl|br|tl|tr`), `r_max`, `r_min` (in screen widths)
     - `orbs`: `r_min`, `r_max` (in screen widths)
     - `capsules`: `angle` (deg), `thickness` (0.2–0.4 widths), `spacing` (0.6–1.0)
     - `dunes`: `tilt` (-0.25–0.25), `top`, `bottom`
     - `tiers`: `top`, `bottom`
     - `petals`: `mode` (`flower|fan`), `count` (5–12), `length` (0.5–0.9 widths),
       `width` (0.12–0.3), `tip` (`pointed|round`), `cx`, `cy`, `spread` (fan degrees).
       Looks lovely with `opacity` 0.85–0.92 so overlaps blend.
     - `bauhaus`: `cols` (3–5), `top` (where the grid starts, keep ≥ 0.3),
       `mix` (weights, e.g. `{"quarter": 3, "half": 2, "circle": 1, "none": 1}`).
       Tiles cycle through the layer colours, so 4–6 layers works best.
     - `squircles`: `exponent` (4–6; higher is squarer), `rotation` (deg), `cx`, `cy`,
       `r_max`, `r_min` (half-size in widths)
     - `folds`: `tilt` (-0.2–0.2), `top`, `bottom`
     - `horizon`: `horizon` (0.48–0.65), `sun_r` (0.12–0.35 widths), `sun_x`,
       `sun_rise` (0 = sitting on the horizon, 1 = fully risen), `curve` (0–0.06).
       Layer 0 is the sun, so pick a colour that stands out from the bands.
     - `ribbons`: `width` (0.15–0.32 widths), `amplitude` (0.04–0.2), `frequency`
       (0.3–1.2), `angle` (deg), `top` (where the rounded heads start; use ≥ 0.3 to
       keep the clock area clear, or -0.2 for full-height ribbons)
     - `blobs`: `wobble` (0.08–0.25), `r_min`, `r_max`
     - `topo`: `wobble` (0.08–0.22), `cx`, `cy`, `r_max`, `r_min`. 5–8 layers;
       alternating close tones reads best.
5. Render: `python generator/render.py specs/<date>.json`. This writes
   `latest/light.png`, `latest/dark.png`, `latest/preview.png`, `latest/manifest.json`.
6. **Look at `latest/preview.png`** (Read it). Each row (light, then dark) shows the
   portrait view on the left and the landscape view on the right; both must work.
   Critique it honestly: balance in each view, focal shapes cut off in one view, too
   busy or too empty, muddy contrast, clashing tan/blue values, shapes crowding the
   clock area or the fold, dark version too bright. If it isn't something you'd be
   happy to see on your phone all day, change the seed, colours or params and
   re-render. Up to 4 attempts; keep the best.
7. Commit and push to the default branch:
   ```bash
   git add specs/<date>.json latest/
   git commit -m "Wallpaper <date>: <title>"
   git push
   ```
   If the push is rejected, `git pull --rebase` and push again. Never force-push.
8. Report the title, style, and a one-line description.
