# 3D Print Advisor — Klipper + OrcaSlicer AI Skill

An AI agent skill that discovers your Klipper 3D printer hardware via the Moonraker API, understands your specific setup and modifications, and generates optimized OrcaSlicer profiles tailored to what you're actually printing.

Built for modded printers. Stock profiles don't know about your upgraded hotend, direct drive conversion, linear rails, or custom cooling. This skill does.

## What It Does

- **Auto-discovers your hardware** — connects to Moonraker, pulls your full Klipper config, and identifies your kinematics, steppers, drivers, input shaper, installed macros, and more
- **Detects OrcaSlicer** — finds your local OrcaSlicer installation and profile directory (macOS, Linux, Windows/WSL)
- **Asks what you're printing** — doesn't just offer "fast/medium/slow" tiers. Asks about print intent: functional part? miniature with fine detail? fast prototype? flexible wearable? Each gets very different settings
- **Generates optimized profiles** — machine, process, and filament profiles as OrcaSlicer-compatible JSON, clamped to your actual hardware limits
- **Knows your bottlenecks** — bed-slinger Y-axis limits, hotend volumetric flow ceiling, StealthChop torque penalty, extruder type constraints
- **Guides calibration** — full calibration toolkit with correct ordering, scope (what's per-filament vs per-printer), and tool recommendations including OrcaSlicer's built-in calibration suite
- **Remembers your setup** — persists your printer profile and calibration state between sessions

## Requirements

- **Klipper firmware** with **Moonraker** API accessible on your network (no auth needed on LAN)
- **OrcaSlicer** installed on the same machine or accessible for profile import
- **Python 3.6+** (for profile generation script)
- **curl** (for Moonraker API access)
- An AI coding agent that supports skills (e.g., [OpenCode](https://opencode.ai), Claude Code)

## Installation

### For OpenCode / Claude Code

Clone this repo into your skills directory:

```bash
# OpenCode
git clone https://github.com/santiagomoneta/3dprint-advisor.git ~/.agents/skills/3dprint-advisor

# Or wherever your agent loads skills from
```

The skill triggers automatically when you ask about 3D printing, slicer profiles, print settings, calibration, Klipper tuning, or OrcaSlicer configuration.

### First Run

The skill detects it's a fresh install (no `state/profile_context.json`) and walks you through setup:

1. **Detects your OS** and finds OrcaSlicer
2. **Asks about your printer** — base model, mods, Klipper IP
3. **Connects to Moonraker** and pulls your full config automatically
4. **Asks about gaps** — hotend model, extruder type, cooling (things not in Klipper config)
5. **Identifies bottlenecks** — per-axis accel limits, volumetric flow ceiling, driver mode penalties
6. **Saves everything** to `state/profile_context.json` for future sessions

## Print Intent Profiles

Instead of generic "Quality / Standard / Draft" tiers, profiles are generated based on what you're actually making:

| Intent | Layer Height | Speed | Use Case |
|--------|-------------|-------|----------|
| **Functional** | 0.20mm | Medium | Brackets, mounts, enclosures, clips |
| **Visual** | 0.12mm | Slow | Vases, decorations, display pieces |
| **Miniature** | 0.08mm | Very slow | Tabletop minis, figurines, fine detail (ironing enabled) |
| **Prototype** | 0.24mm | Fast | Test fits, drafts, speed over quality |
| **Wearable** | 0.20mm | Slow | TPU/flex parts, phone cases, gaskets |
| **Structural** | 0.20mm | Medium | Load-bearing parts, high wall count, dense infill |

Every setting is clamped to your printer's actual limits — speeds are capped by max velocity and volumetric flow, accelerations by per-axis limits.

## Calibration Guidance

The skill includes a comprehensive calibration toolkit covering:

### Per-Printer (do once)
- Belt tension (frequency measurement with phone mic app)
- Input shaper (ADXL345 + `SHAPER_CALIBRATE`)
- `AUTO_SPEED` / `TEST_SPEED` for max accel/velocity
- Skew correction
- Rotation distance (e-steps)

### Per-Filament (do once per material, valid for ALL process profiles)
- Temperature tower
- Max volumetric flow
- Flow rate (extrusion multiplier)
- Retraction length/speed
- Pressure Advance — static (single value) or **Adaptive PA** (recommended if you use multiple process profiles)

Key insight: **you do NOT need to re-calibrate filament when switching process profiles** (e.g., from functional to miniature). The per-filament calibration is valid across all profiles. The one exception is Pressure Advance, which varies with speed/accel — but OrcaSlicer's Adaptive PA solves this with a one-time multi-speed calibration.

## Supported Hardware

Works with any Klipper printer accessible via Moonraker. Tested/designed for:

- **Bed-slingers**: Ender 3 (all variants), CR-10, Anycubic i3 Mega, Prusa MK3S
- **CoreXY**: Voron 0/2.4/Trident, VzBot, RatRig V-Core, custom builds
- **Common mods**: Direct drive conversions (BMG, Orbiter, Sherpa), all-metal hotends (Dragon, Rapido, Spider, Revo, Mosquito), linear rails, BLTouch/CRTouch/Klicky/Tap, dual Z, ADXL345 input shaper

The hotend database includes flow limits for 20+ hotend models to automatically set volumetric speed caps.

## File Structure

```
3dprint-advisor/
├── SKILL.md                              # Skill instructions (loaded by the AI agent)
├── README.md                             # This file
├── LICENSE                               # MIT
├── .gitignore
├── scripts/
│   ├── detect_environment.sh             # OS + OrcaSlicer auto-detection
│   ├── fetch_klipper_config.sh           # Moonraker API config fetcher
│   └── generate_profile.py              # OrcaSlicer JSON profile generator
├── references/
│   ├── print_intent_profiles.md          # Intent → settings decision matrix
│   ├── calibration_toolkit.md            # Full calibration guide with scope + ordering
│   ├── hotend_database.md                # 20+ hotends with flow limits
│   └── orca_klipper_mapping.md           # OrcaSlicer ↔ Klipper setting mapping
├── state/                                # Created on first run (gitignored)
│   └── .gitkeep
└── output/                               # Generated profiles land here (gitignored)
    └── .gitkeep
```

## Usage Examples

Once installed, just talk to your AI agent:

```
> I need a profile for printing a miniature — it's a 15cm anime figure with lots of small details

> Generate me a PETG functional profile for printing enclosure panels

> What are my current Klipper settings?

> I'm getting ringing on Y axis, what should I check?

> Walk me through calibrating a new roll of PETG

> Review my Klipper config for issues
```

## Scripts

### `detect_environment.sh`
```bash
bash scripts/detect_environment.sh
# Output: JSON with os, orcaslicer_path, version, profile_dir
```

### `fetch_klipper_config.sh`
```bash
bash scripts/fetch_klipper_config.sh http://<printer-ip>:7125
# Output: JSON with full parsed config, live state, installed macros
```

### `generate_profile.py`
```bash
# Generate functional PLA profile
python3 scripts/generate_profile.py \
  --context state/profile_context.json \
  --intent functional --filament PLA \
  --output-dir ./output

# Generate all intents + all filaments
python3 scripts/generate_profile.py \
  --context state/profile_context.json \
  --all-intents --all-filaments \
  --output-dir ./output

# List available intents and filaments
python3 scripts/generate_profile.py --context state/profile_context.json --list-intents
python3 scripts/generate_profile.py --context state/profile_context.json --list-filaments
```

## Contributing

PRs welcome. Particularly useful:
- Adding hotend models to `references/hotend_database.md`
- Testing on different printer types (delta, CoreXZ, etc.)
- Adding filament profiles for specialty materials (nylon, PC, CF blends)
- Improving the intent presets based on real-world printing experience

## License

MIT
