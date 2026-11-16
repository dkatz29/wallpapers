# iPhone Duo daily wallpapers

A new flat, abstract wallpaper every day, in a **light** version for daytime and a
**dark** version for night. Sized for the iPhone Duo inner display (1878 × 2670); the
outer display lines up with it. Only blues, teals, tans, khakis and greys.

![Today's wallpaper](latest/preview.png)

## How it works

```
 00:00 CT  Claude routine ──► runs the duo-wallpaper skill
                              ├─ designs specs/<date>.json (style, colours, seed)
                              ├─ python generator/render.py ──► latest/light.png, latest/dark.png
                              ├─ reviews latest/preview.png, iterates if it's not good
                              └─ git commit + push
 Sunrise   iOS automation ──► "Duo Wallpaper" shortcut (light) ──► downloads latest/light.png ──► sets wallpaper
 Sunset    iOS automation ──► "Duo Wallpaper" shortcut (dark)  ──► downloads latest/dark.png  ──► sets wallpaper
```

GitHub is the hand-off between Claude and the phone. The image URLs never change:

- Light: `https://raw.githubusercontent.com/dkatz29/wallpapers/main/latest/light.png`
- Dark:  `https://raw.githubusercontent.com/dkatz29/wallpapers/main/latest/dark.png`
- Info:  `https://raw.githubusercontent.com/dkatz29/wallpapers/main/latest/manifest.json`

| Path | What |
|---|---|
| `.claude/skills/duo-wallpaper/SKILL.md` | The Claude skill: design brief and nightly steps |
| `generator/render.py` | Turns a spec into the light/dark PNGs; enforces size and palette |
| `specs/` | One JSON spec per day. Any past wallpaper can be re-rendered from it |
| `latest/` | Today's `light.png`, `dark.png`, `preview.png`, `manifest.json` |

Only the specs are archived. Past images can be rebuilt exactly with
`python generator/render.py specs/<date>.json --out tmp/`.

## iOS Shortcut setup (one time, about 5 minutes)

**Before you start:** set any **photo** wallpaper once by hand (Settings → Wallpaper).
The *Set Wallpaper Photo* action updates the current photo wallpaper.

### 1. The shortcut, "Duo Wallpaper"

Shortcuts app → **+** → name it `Duo Wallpaper`. Open its settings (ⓘ) → turn on
**Use as Quick Action / Receive input**, input type **Text**, and choose
*If there's no input:* **Ask For → Text** so you can also run it by hand.

Add these actions:

1. **Text** → `https://raw.githubusercontent.com/dkatz29/wallpapers/main/latest/`
   then insert the **Shortcut Input** variable, then type `.png?t=`, then insert
   **Current Date** (tap it → Date Format: *Custom* → `yyyyMMddHHmm`).
   The `?t=…` part makes sure GitHub never serves a stale cached copy.
2. **Get Contents of URL** → URL: the *Text* from step 1. (Method GET, no headers;
   the repo is public.)
3. **Set Wallpaper Photo** → Photo: *Contents of URL*.
   - Wallpaper: **Lock Screen and Home Screen**
   - Expand the action and turn **off** *Show Preview* and *Crop to Subject*
     (otherwise it stops and asks you to confirm).

To test it, run the shortcut and type `light` or `dark`.

### 2. The automations

Shortcuts → **Automation** → **+** → **Time of Day**:

| Automation | Trigger | Action |
|---|---|---|
| Wallpaper: light | **Sunrise** (offset 0) · Daily | **Text** `light` → **Run Shortcut** *Duo Wallpaper* (Input: *Text*) |
| Wallpaper: dark | **Sunset** (offset 0) · Daily | **Text** `dark` → **Run Shortcut** *Duo Wallpaper* (Input: *Text*) |

For both, choose **Run Immediately** and turn off **Notify When Run**.

The midnight job replaces `latest/` around 00:00 CT. Sunset always uses the dark
version of that day's design, and the next sunrise picks up the new one.

## The midnight Claude routine

A scheduled Claude Code routine runs daily at 00:00 America/Chicago against this
repo with this prompt:

> Use the duo-wallpaper skill to design, render, review and push today's wallpaper.

To run it by hand from a clone: open Claude Code in the repo and say
*"generate today's Duo wallpaper"*.

## Local use

```bash
pip install -r requirements.txt
python generator/render.py --palette              # allowed colour names
python generator/render.py specs/2026-11-16.json   # renders into latest/
```
