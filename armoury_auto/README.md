# Armoury Auto

Switches the ASUS Armoury Crate **performance mode** (Silent / Performance / Turbo) and
**GPU mode** (Eco = NVIDIA GPU off / Standard = on) automatically, based on how you use
the laptop. It talks to the same ASUS ACPI driver Fn+F5 uses and also switches the matching
Windows power plan, so Armoury Crate stays in sync. Built for an ASUS TUF Gaming A16
(FA608PP, RTX 5070); no admin rights needed. Starts with Windows (tray menu toggle).

## Current setup
| When | Mode | NVIDIA GPU |
|---|---|---|
| Plugged in | Turbo | asks you once per plug-in (Yes = on, No = Eco) |
| Battery under 20% | Silent | Eco |
| Battery + CPU over 70% for 30 s | Turbo | on |
| Battery + integrated GPU over 80% for 20 s | Turbo | on |
| Battery + no input for 5 min | Silent | Eco |
| Battery, 06:00-12:00 | Performance | Eco |
| Battery, 12:00-16:00 Mon-Fri (college) | Silent | Eco |
| Battery, 16:00-06:00 | Performance | Eco |

Reminder toast at 15:45 Mon-Fri before college ends.

**Manual changes are detected.** If you change the mode (Fn+F5, Armoury Crate, Windows power
menu) or the GPU mode yourself, the app leaves it alone for 15 minutes. Plugging in or
unplugging restarts the rules immediately.

**The NVIDIA GPU is never cut while an app uses it.** Before switching to Eco the app checks
`nvidia-smi`; if a game or other app holds the GPU it waits and tells you what to close
(tray: "Turn off NVIDIA GPU anyway" to force it). Apps known to cope with it are listed
in `gpu_safe_to_cut_apps`.

**GPU switching needs Standard as the base.** In Ultimate mode (screen wired straight to the
NVIDIA GPU) Eco is impossible without a restart, so the app only switches the performance
mode. Set GPU Mode to **Standard** in Armoury Crate once and restart. Don't use
Armoury Crate's "Optimized" GPU mode; it switches on its own and would fight this app.

## Tray icon
Coloured circle: green **S** = Silent, blue **P** = Performance, red **T** = Turbo,
grey = paused. A small green dot = NVIDIA GPU is on. Grey crossed-out ring = app disabled.

Right-click menu:
- **Enable Armoury Auto**: untick to switch the app off completely (nothing is switched,
  no pop-ups or reminders). Remembered after restarts (`state.json`); tick it to turn it back on.
- **Pause for 1 hour** / **Resume rules now**
- **Automatic** or **Lock** a mode
- **NVIDIA GPU on while charging**, **Turn off NVIDIA GPU anyway**
- Edit rules, open the log, Start with Windows, Quit

## Commands
- `pythonw app.py`: run in the tray
- `python app.py --status`: show current usage and which rule matches
- `python app.py --dry-run`: run in the console and log decisions without switching
- `python app.py --set turbo`: switch once and exit

## Rules (`config.json`)
Rules are checked **top to bottom; the first rule whose conditions are all true wins**.
Each rule sets `mode` and optionally `gpu` (`eco`, `standard`, or `ask`). If none match,
`default_mode` / `default_gpu` are used. The file reloads automatically when you save it.

| Condition | Example | Meaning |
|---|---|---|
| `apps` | `["cs2", "blender.exe"]` | one of these programs is running (`.exe` optional) |
| `match` | `"foreground"` | with `apps`: only when that app is the active window (default `"running"`) |
| `plugged_in` / `on_battery` | `true` | power source |
| `battery_below` | `30` | on battery and below this % |
| `cpu_above` / `cpu_below` | `70` | average CPU % over `for_seconds` (default 10) |
| `gpu_above` | `80` | average 3D load of the busiest GPU over `for_seconds` |
| `idle_minutes` | `5` | no keyboard/mouse input for this long |
| `between` | `["23:30", "07:00"]` | time of day (can wrap past midnight) |
| `days` | `["mon", "fri"]` | days of the week |
| `enabled` | `false` | turn a rule off without deleting it |

`reminders`: `{"at": "15:45", "days": [...], "title": "...", "message": "..."}` shows a toast.

Global settings: `check_interval_seconds`, `min_seconds_between_switches`,
`min_minutes_between_gpu_switches`, `respect_manual_change_minutes` (0 = never pause),
`notify_on_switch`, `power_plans` (Windows plan names Armoury Crate created per mode).
