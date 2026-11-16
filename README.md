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

Shortcut **ⓘ / Details** → turn on **Receive Text input**, and set *If there's no input*
to **Continue**. The URLs are fixed in the shortcut, not built from what you type
(typed text can be blank, auto-capitalised or carry a hidden line break, and each of
those gives a 404). With no input it defaults to light.

| # | Action | Settings |
|---|---|---|
| 1 | **Change Case** | *Shortcut Input* → **lowercase** |
| 2 | **If** | *Updated Text* **contains** `dark` |
| 3 | &nbsp;&nbsp;**Text** | `https://raw.githubusercontent.com/dkatz29/wallpapers/main/latest/dark.png` |
| 4 | **Otherwise** | |
| 5 | &nbsp;&nbsp;**Text** | `https://raw.githubusercontent.com/dkatz29/wallpapers/main/latest/light.png` |
| 6 | **End If** | |
| 7 | **Get Contents of URL** | URL: **If Result** |
| 8 | **Get Details of Images** | **Width** of *Contents of URL* |
| 9 | **If** | *Width* **is** `1878` |
| 10 | &nbsp;&nbsp;**Set Wallpaper Photo** | *Contents of URL* · Lock Screen and Home Screen · *Show Preview* off · *Crop to Subject* off |
| 11 | **Otherwise** | |
| 12 | &nbsp;&nbsp;**Show Notification** | `Duo wallpaper download failed` |
| 13 | **End If** | |

The width check in step 9 stops an error page from ever becoming the wallpaper.
Test by running it with no input; you should get the light version.

### 2. The automations

Shortcuts → **Automation** → **+** → **Time of Day**:

| Automation | Trigger | Actions |
|---|---|---|
| Wallpaper: light | **Sunrise** · Daily | **Run Shortcut** *Duo Wallpaper* (no input, so it uses light) |
| Wallpaper: dark | **Sunset** · Daily | **Text** `dark` → **Run Shortcut** *Duo Wallpaper* (Input: *Text*) |

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
