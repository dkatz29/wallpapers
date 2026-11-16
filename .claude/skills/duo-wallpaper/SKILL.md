---
name: duo-wallpaper
description: Design and publish the day's abstract light + dark wallpaper pair for the iPhone Duo inner display (1878x2670), then commit and push so the iOS Shortcut can pick it up at sunrise/sunset. Use when asked to generate, regenerate, or publish the daily Duo wallpaper, or when the midnight routine runs.
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
- **Inner display only:** 1878 × 2670. The outer display lines up with it, so don't
  make a separate outer image.
- **Light version** (sunrise to sunset): background from `light` (optionally `mid`)
  tones, layers mostly `light`/`mid`, with one or two richer `mid` accents.
- **Dark version** (sunset to sunrise): background from `dark` tones only; layers
  mostly `dark` with at most one or two muted `mid` accents. Keep it low-glare. It
  should feel like the same wallpaper at night, not a different one.
- Keep the top ~15% fairly quiet (lock-screen clock) and avoid high-contrast detail
  straight down the vertical centre line (the fold).

## Steps

1. `cd` to the repo root. Ensure Pillow is available: `pip install -q -r requirements.txt`.
2. Work out today's date **in America/Chicago**: `TZ=America/Chicago date +%F`. The
   routine runs at local midnight, so this is the day the wallpaper will be shown.
   If `specs/<date>.json` already exists, only regenerate when explicitly asked.
3. Look at the last 7 files in `specs/` and **don't repeat** the previous day's
   `style`, and don't reuse a style + dominant colour pairing from the past week.
   Vary the mood across the week: sandy/khaki days, oceanic blue days, grey/teal days.
4. Write `specs/<date>.json`:

   ```json
   {
     "date": "2026-11-17",
     "title": "Two-word evocative name",
     "seed": 48213,
     "style": "waves | arcs | orbs | capsules | dunes | tiers",
     "params": {},
     "light": { "background": ["linen", "sand"], "layers": ["mist", "sky", "lagoon", "teal"] },
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
5. Render: `python generator/render.py specs/<date>.json`. This writes
   `latest/light.png`, `latest/dark.png`, `latest/preview.png`, `latest/manifest.json`.
6. **Look at `latest/preview.png`** (Read it). Critique it honestly: balance, too
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
