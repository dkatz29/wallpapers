---
name: duo-wallpaper
description: Design and publish the day's abstract light + dark wallpaper pair for the iPhone Duo inner display (1878x2670, composed so the landscape view shows the whole design), then commit and push so the iOS Shortcut can pick it up at sunrise/sunset. Use when asked to generate, regenerate, or publish the daily Duo wallpaper, or when the midnight routine runs.
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
- **One 1878 × 2670 portrait image, composed for landscape first.** The outer
  display shows nearly the same view as inner portrait, so don't make a separate
  outer image. In **landscape** on the inner display, iOS shows only a band of the
  image (y ≈ 0.08–0.575, measured on the phone), and a Shortcut can't change that.
  So the renderer composes every design in a **landscape-shaped frame that is exactly
  that band**:
  - All positions (`cx`, `cy`, `top`, `bottom`, `horizon`, …) are **frame
    coordinates**: x 0–1 across, y 0–1 down the landscape view. Landscape shows the
    whole frame, so compose a complete, balanced landscape picture in it.
  - In portrait the frame sits in the upper part of the screen. The banded styles
    automatically continue below it with gentle extra bands, and pattern styles
    (`stripes`, `dots`, `prisms`, `scales`, `bars`, `arches`, `steps`) fill the whole image.
    Centred-object styles (`orbs`, `petals`, `topo`, `twist`, `moons`, `cards`, …)
    leave calm background below. That's expected; just make sure portrait looks
    intentional, not cut off.
  - Sizes (`r_*`, `length`, `width`, `thickness`, `sun_r`) are in **frame heights**
    (the landscape screen's short side). For banded styles, `"echo": false` turns off
    the portrait-only continuation bands.
- **Light version** (sunrise to sunset): background from `light` (optionally `mid`)
  tones, layers mostly `light`/`mid`, with one or two richer `mid` accents.
- **Dark version** (sunset to sunrise): background from `dark` tones only; layers
  mostly `dark` with at most one or two muted `mid` accents. Keep it low-glare. It
  should feel like the same wallpaper at night, not a different one.
- The lock-screen clock is large: about frame y 0.1–0.4 in landscape (and the top
  of the frame in portrait). Bold flat shapes behind it are fine; avoid fine
  high-contrast detail there. Avoid high-contrast detail straight down the vertical
  centre line (the fold).

## Steps

1. `cd` to the repo root. Ensure Pillow is available: `pip install -q -r requirements.txt`.
2. Work out today's date **in America/Chicago**: `TZ=America/Chicago date +%F`. The
   routine runs at local midnight, so this is the day the wallpaper will be shown.
   If `specs/<date>.json` already exists, only regenerate when explicitly asked.
3. Look at the last 14 files in `specs/` and **rotate styles**: never use a style that
   appeared in the last 7 days, and prefer the styles used least recently (or never).
   There are 28 styles; use them all over time. Also don't repeat the previous day's
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
   | `stripes` | Bold flat stripes of varying width, straight or tilted |
   | `ripples` | Two or three sets of concentric circles overlapping |
   | `mountains` | Layered flat mountain ranges with sharp peaks |
   | `dots` | Calm grid of dots that swell in size and colour across the image |
   | `chevrons` | Stacked zig-zag bands, like a flat textile |
   | `sunburst` | Flat rays from a point with a disc at the centre (mid-century) |
   | `moons` | A row of two-tone moon phases over a large soft disc |
   | `prisms` | Big low-poly triangles forming a faceted gradient |
   | `steps` | Rounded blocks stepping down like a staircase |
   | `bars` | Upright pills of varying height in a row, like a calm equaliser |
   | `twist` | Nested rounded squares, each turned a little further |
   | `scales` | Overlapping rows of concentric half-rings (seigaiha / fish scales) |
   | `arches` | Mid-century arches: nested doorway or a row of arched windows |
   | `cards` | Rounded cards fanned and stacked diagonally |

   Even within a style, push variety with `params` (angle, corner, mode, count, scale)
   so two `petals` days don't look alike.
4. Write `specs/<date>.json`:

   ```json
   {
     "date": "2026-11-17",
     "title": "Two-word evocative name",
     "seed": 48213,
     "style": "one of the 28 styles above",
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
     - `arcs`: `corner` (`bl|br|tl|tr`), `r_max`, `r_min` (frame heights)
     - `orbs`: `r_min`, `r_max` (frame heights)
     - `capsules`: `angle` (deg), `thickness` (0.2–0.4), `spacing` (0.6–1.0)
     - `dunes`: `tilt` (-0.25–0.25), `top`, `bottom`
     - `tiers`: `top`, `bottom`
     - `petals`: `mode` (`flower|fan`), `count` (5–12), `length` (0.5–0.9),
       `width` (0.12–0.3), `tip` (`pointed|round`), `cx`, `cy`, `spread` (fan degrees).
       Looks lovely with `opacity` 0.85–0.92 so overlaps blend.
     - `bauhaus`: `cols` (3–5), `top` (where the grid starts, keep ≥ 0.25),
       `mix` (weights, e.g. `{"quarter": 3, "half": 2, "circle": 1, "none": 1}`).
       Tiles cycle through the layer colours, so 4–6 layers works best.
     - `squircles`: `exponent` (4–6; higher is squarer), `rotation` (deg), `cx`, `cy`,
       `r_max`, `r_min` (half-size in frame heights)
     - `folds`: `tilt` (-0.2–0.2), `top`, `bottom`
     - `horizon`: `horizon` (0.45–0.7), `sun_r` (0.12–0.35), `sun_x`,
       `sun_rise` (0 = sitting on the horizon, 1 = fully risen), `curve` (0–0.06).
       Layer 0 is the sun, so pick a colour that stands out from the bands.
     - `ribbons`: `width` (0.15–0.32), `amplitude` (0.04–0.2), `frequency`
       (0.3–1.2), `angle` (deg), `top` (where the rounded heads start; use ≥ 0.2 to
       keep the clock area clear, or -0.2 for full-height ribbons)
     - `blobs`: `wobble` (0.08–0.25), `r_min`, `r_max`
     - `topo`: `wobble` (0.08–0.22), `cx`, `cy`, `r_max`, `r_min`. 5–8 layers;
       alternating close tones reads best.
     - `stripes`: `angle` (deg; 0 = vertical, 90 = horizontal), `repeat` (1–2: cycles
       through the layers once or twice)
     - `ripples`: `sets` (2–3 ring centres), `r_max` (0.5–0.9)
     - `mountains`: `top`, `bottom`, `height` (0.2–0.35 peak height)
     - `dots`: `cols` (5–10), `offset` (true = staggered rows). Colour follows dot
       size, so order layers light → strong.
     - `chevrons`: `teeth` (1–3 per width), `amplitude` (0.06–0.18), `top`, `gap` (0.1–0.2)
     - `sunburst`: `cx`, `cy`, `rays` (12–24), `r` (centre disc, 0.1–0.25). The last
       layer is the disc.
     - `moons`: `count` (3–5), `cy`, `arc` (0–0.15), `r`, `halo` (0.4–0.65). Layer 0
       is moonlight, the last layer is shadow, layer 1 is the halo disc.
     - `prisms`: `cols` (4–6), `jitter` (0.05–0.25), `angle` (deg, direction of the
       colour gradient). Order layers as a gradient.
     - `steps`: `direction` (`left|right`), `radius` (0.03–0.12 corner rounding)
     - `bars`: `count` (5–12), `gap` (0.15–0.5 of bar width)
     - `twist`: `exponent` (3–5), `twist` (deg per layer, ±4–12), `cx`, `cy`, `r_max`, `r_min`
     - `scales`: `cols` (2–4; 2 is calm, 4 is busy), `rings` (2–4)
     - `arches`: `mode` (`nested|row`), `cx` (nested), `count` (row, 3–5)
     - `cards`: `rotation` (deg), `spread` (deg per card), `w`, `h` (card size)
5. Render: `python generator/render.py specs/<date>.json`. This writes
   `latest/light.png`, `latest/dark.png`, `latest/preview.png`, `latest/manifest.json`.
6. **Look at `latest/preview.png`** (Read it). Each row (light, then dark) shows the
   portrait view on the left and the inner landscape view (the whole frame) on the
   right. Landscape is the primary composition; portrait must still look
   intentional. Critique it honestly: balance in each view, too
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
