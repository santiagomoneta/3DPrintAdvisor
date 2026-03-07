---
name: 3dprint-advisor
description: 3D printing advisor for Klipper + OrcaSlicer. Discovers printer hardware via Moonraker API, detects local OrcaSlicer installation, generates optimized slicer profiles based on print intent (functional, visual, miniature, etc.), and provides interactive tuning guidance. Use when asked about 3D printing, slicer profiles, print settings, calibration, Klipper tuning, or OrcaSlicer configuration.
---

# 3D Print Advisor — Klipper + OrcaSlicer

Discovers your printer, understands your hardware, generates optimized OrcaSlicer profiles for specific print intents, and advises on calibration and tuning.

## First-Run Detection

Check if `~/.agents/skills/3dprint-advisor/state/profile_context.json` exists.

- **If missing**: Run the full onboarding flow (Phase 1 below)
- **If present**: Read it, greet the user with a summary of their known setup, and ask what they need

## Phase 1: Onboarding (first run only)

Run these steps sequentially. Use the `question` tool to gather what can't be auto-detected.

### Step 1: Detect local environment

Run `scripts/detect_environment.py` to auto-detect OS, OrcaSlicer path, and profile directory.

### Step 2: Printer Discovery & Selection

1.  List all `.json` files in the OrcaSlicer `machine` folder.
2.  Use the `question` tool to ask the user:
    - **Which printer profile is your primary?** (Provide list of discovered machine profiles).
    - **Is this printer stock or modded?** (Stock / Modded).

### Step 3: Granular Hardware Discovery (Choice-based)

If modded, walk the user through a detailed checklist of common 3D printer mods in batches. Each question must provide the most common industry-standard options and an "Other" option for manual text entry.

**Batch 1 — Motion & Frame**:
- **Z-Axis Setup**: (Single Z-Screw, Dual Z-Screws (Mechanical), Independent Dual Z, Belted Z, Other).
- **Motion System**: (X-Axis Linear Rails, Y-Axis Linear Rails, Z-Axis Linear Rails, Stock Wheels, Other) [Multi-select].
- **Stepper Motors**: (Stock Motors, Upgraded LDO/Moons, Pancake E-axis only, Other).

**Batch 2 — Extruder & Cooling**:
- **Extruder Mounting**: (Direct Drive (DD), Bowden Setup, Other).
- **Hotend Model**: (Creality Stock (PTFE), Creality (All-Metal), Upgraded (Spider/Dragon/etc.), Other).
- **Cooling Blowers**: (Single 4010 Fan, Single 5015 Fan, Dual 5015 Fans (e.g. Hero Me), 4020 Blower Fan, Other) [Multi-select].

**Batch 3 — Bed & Mainboard**:
- **Mainboard Model**: (Creality (Stock) Board, BTT (SKR/Mini E3), MKS/Octopus/Spider, Other).
- **Probing & Bed Surface**: (BLTouch (Probe) Upgrade, PEI Textured Surface Upgrade, Inductive Upgrade, Other) [Multi-select].

### Step 4: Klipper Access (if applicable)

- Ask for Moonraker IP/Hostname.
- Test connectivity and run `scripts/fetch_klipper_config.py <ip>`.

### Step 5: Filaments & Brands

- Ask for filaments: (PLA, PETG, TPU, ABS, ASA, Nylon).
- Ask for preferred brands (Text input).

### Step 6: Validate & Identfy Bottlenecks
(As described in previous version)

### Step 4: Validate Moonraker data

If Moonraker is reachable, run `scripts/fetch_klipper_config.py <ip>` and parse:
- `[printer]` — kinematics, max_velocity, max_accel
- `[extruder]` — rotation_distance, nozzle_diameter, pressure_advance, max_extrude_cross_section
- `[input_shaper]` — shaper types and frequencies
- `[firmware_retraction]` — retract_length, speeds
- `[stepper_x/y/z]` — position_max (build volume), rotation_distance
- `[tmc2209 stepper_*]` — run_current, stealthchop_threshold
- `[bed_mesh]` — mesh bounds
- `[bltouch]` or `[probe]` — z_offset
- `[heater_bed]` — max_temp (indicates bed capability)
- Installed macros: KAMP, TEST_SPEED, AUTO_SPEED, firmware_retraction, exclude_object, gcode_arcs, skew_correction
- Live state: current PA, toolhead accel, temperatures

Present a hardware summary to the user and ask them to confirm or correct.

### Step 5: Identify hardware bottlenecks

Based on the gathered data, automatically determine:

| Check | How |
|-------|-----|
| Bed-slinger Y limit | `kinematics=cartesian` → Y accel capped at 2000-3000 |
| Volumetric flow limit | Look up hotend model in `references/hotend_database.md` |
| StealthChop penalty | `stealthchop_threshold=999999` → reduced torque at high speed |
| Input shaper aggressiveness | `3hump_ei` or `2hump_ei` → complex resonance — flag belt tension check before re-running shaper |
| Belt tension unknown | No Klipper setting — ask user if/when belts were last checked. Recommend frequency measurement with phone mic app (Gates Carbon Drive, Spectroid, guitar tuner). Target ~80-120Hz for GT2 6mm |
| Extruder torque | Cross-reference motor type + run_current + gear ratio |
| Bowden vs direct | Infer from `rotation_distance` (>30 = bowden with gear, <10 = direct drive with gear) |
| Cooling capacity | User-reported; affects bridge/overhang speed limits |
| Enclosure | Affects material selection and max ambient temp |

### Step 6: Detect and install missing Klipper extras

After discovering the printer's current config, audit which optional Klipper modules/macros are missing and offer to install them. This is critical for newbie users with fresh Klipper installs.

**Audit**: Run `scripts/install_klipper_extras.sh <moonraker_url> --check` to get a JSON report of what's installed vs missing. Reference `references/klipper_extras_database.md` for the full list and installation priority.

**Present findings** to the user using the `question` tool. Group by priority:

**Critical (should always install)**:
- `exclude_object` — Required for object cancellation and KAMP
- `firmware_retraction` — Required for KAMP purge, enables runtime retraction tuning
- `gcode_arcs` — Arc support for smoother curves and smaller gcode files

**Recommended (significant quality-of-life improvements)**:
- KAMP — Adaptive bed meshing + smart purge placement
- TEST_SPEED macro — Quick speed/accel validation
- `skew_correction` — Frame squareness compensation (just enables the section)
- `axis_twist_compensation` — Gantry twist correction (bed-slingers especially)

**Optional (for users who want to push limits)**:
- klipper_auto_speed — Automated max accel/velocity binary search
- `resonance_tester` + `input_shaper` — If accelerometer present and not already configured

**Installation flow**:
1. Show the user what's missing with a brief explanation of each
2. Ask which they want to install (allow multiple selection, recommend all critical + recommended)
3. Run `scripts/install_klipper_extras.sh <moonraker_url> <extra1> <extra2> ...`
4. The script handles: config injection via Moonraker file API, SSH to Klipper host for git clones, moonraker.conf updates, and automatic service restarts
5. After install, re-run `scripts/fetch_klipper_config.py` to verify the new config sections are active
6. If SSH fails for third-party modules (auto_speed, KAMP), provide the manual commands the user can paste into their SSH terminal

**SSH access**: Third-party modules (auto_speed, KAMP) require SSH to the Klipper host. If this is the first time, ask the user:
- Do you have SSH access to your printer? (most Klipper setups do — `ssh pi@<printer-ip>`)
- Have you set up SSH keys? If not, provide instructions for `ssh-copy-id`

**Track installed extras** in `profile_context.json` under `klipper.installed_extras`:
```json
"installed_extras": {
  "firmware_retraction": {"installed": true, "installed_by": "3dprint-advisor"},
  "exclude_object": {"installed": true, "installed_by": "3dprint-advisor"},
  "gcode_arcs": {"installed": true, "installed_by": "3dprint-advisor"},
  "kamp": {"installed": true, "installed_by": "3dprint-advisor"},
  "test_speed": {"installed": true, "installed_by": "3dprint-advisor"},
  "auto_speed": {"installed": false, "reason": "user_declined"}
}
```

### Step 7: Save state

Write everything to `state/profile_context.json`. This is the persistent memory. Format:

```json
{
  "version": 1,
  "created": "ISO-8601",
  "updated": "ISO-8601",
  "environment": {
    "os": "darwin|linux|windows",
    "orcaslicer_path": "/path/to/OrcaSlicer",
    "orcaslicer_version": "2.x.x",
    "orcaslicer_profile_dir": "/path/to/profiles"
  },
  "printer": {
    "name": "My Printer Name",
    "kinematics": "cartesian|corexy|corexz|delta",
    "build_volume": {"x": 235, "y": 235, "z": 250},
    "moonraker_url": "http://<printer-ip>:7125",
    "hotend": {"model": "E3D V6", "max_flow_mm3s": 14, "max_temp": 285},
    "extruder": {"type": "direct|bowden", "gear_ratio": "3:1", "model": "BMG"},
    "nozzle": {"diameter": 0.4, "material": "brass"},
    "bed_surface": "PEI|glass|textured",
    "cooling": {"type": "stock|upgraded", "fans": "description"},
    "enclosure": false,
    "frame_mods": [],
    "probe": "BLTouch|CRTouch|Klicky|Tap|none"
  },
  "klipper": {
    "max_velocity": 300,
    "max_accel": 3000,
    "input_shaper": {"x": {"type": "mzv", "freq": 50.0}, "y": {"type": "mzv", "freq": 40.0}},
    "pressure_advance": 0.04,
    "firmware_retraction": {"length": 0.5, "speed": 60},
    "stealthchop": {"x": false, "y": false, "z": false, "e": false},
    "installed_macros": [],
    "raw_config": {}
  },
  "bottlenecks": {
    "y_accel_limit": null,
    "volumetric_flow_limit": 14,
    "speed_limit_reason": "",
    "notes": []
  },
  "filaments": ["PLA"],
  "generated_profiles": []
}
```

### Step 8: Post-Onboarding Validation Checklist

Once profiles are generated and saved, present a hardware and filament validation checklist to the user to ensure their physical printer matches the new high-performance slicer settings.

**1. Klipper Hardware Validation**:
- **Rotation Distance**: Suggest verifying that 100mm of requested filament actually pulls 100mm, especially if the extruder was upgraded.
- **Max Speed/Accel**: Suggest running the `TEST_SPEED` macro to ensure the frame/motors can handle the configured limits.
- **Belt Tension & Input Shaper**: Remind the user to check belt tension (80-120Hz) and re-run `SHAPER_CALIBRATE` if they have linear rails or recently changed belts.

**2. OrcaSlicer Filament Validation**:
- Suggest running **Temperature Tower**, **Flow Rate**, and **Pressure Advance** calibrations using the newly generated process profile.
- If the user aims for high quality (e.g., miniatures, action figures), suggest a **Bridge Flow Rate** calibration for the specific layer height.

**3. Confirmation**:
- Allow the user to Confirm (already calibrated), Postpone, or Request Help running specific macros.

---

## Phase 2: Profile Generation (interactive)

When the user asks for a profile, DON'T just pick a tier. Ask about **print intent** first.

### Step 1: Ask about the print

Use the `question` tool:

**What are you printing?**
- Functional part (brackets, mounts, enclosures)
- Visual/display piece (vase, decoration, gift)
- Miniature/figurine (detailed, small features)
- Prototype/draft (just need shape, speed matters)
- Wearable/flexible (TPU parts)
- Structural/load-bearing (needs strength)
- Custom (let me describe it)

**What filament?** (from their known list)

**What nozzle?** (default to their configured nozzle, but allow override — some users swap nozzles)

**Any specific requirements?**
- Dimensional accuracy matters
- Surface finish matters
- Strength/layer adhesion matters  
- Speed matters (deadline, batch production)
- Overhangs > 60 degrees
- Bridging required
- Thin walls / fine details
- Large flat surfaces (warping risk)

### Step 2: Map intent to settings

Use `references/print_intent_profiles.md` to determine the optimal settings matrix:

| Intent | Layer H | Walls | Speed | Accel | Infill | Cooling | PA priority |
|--------|---------|-------|-------|-------|--------|---------|-------------|
| **Functional** | 0.20 | 3-4 | Medium | Medium | 20-40% gyroid | Normal | Medium |
| **Visual** | 0.12-0.16 | 3 | Slow | Low | 15-20% | High | High (no blobs) |
| **Miniature** | 0.08-0.12 | 2-3 | Very slow | Very low | 15% | Max | Critical |
| **Prototype** | 0.24-0.28 | 2 | Fast | High | 10-15% | Normal | Low |
| **Wearable/Flex** | 0.20 | 3-4 | Slow | Low | 15-20% | Medium | N/A (TPU) |
| **Structural** | 0.20-0.24 | 4-5 | Medium | Medium | 40-60% cubic | Moderate | Medium |
| **Custom** | Ask | Ask | Ask | Ask | Ask | Ask | Ask |

### Step 3: Apply hardware constraints

Clamp all settings to the user's actual hardware limits from `profile_context.json`:
- Speed capped by `max_velocity` and volumetric flow limit
- Accel capped by per-axis limits (Y for cartesian)
- Flow rate = layer_height * line_width * speed; must not exceed hotend limit
- Retraction adjusted for extruder type (direct/bowden) and filament
- Cooling adjusted for fan setup capability

### Step 4: Generate profile JSON

Run `scripts/generate_profile.py` with the computed settings. Outputs:
- Process profile JSON (the print settings)
- Filament profile JSON (if not already generated for this material)
- Machine profile JSON (if first time, or nozzle changed)

Each JSON follows OrcaSlicer's format with proper `inherits` chains.

### Step 5: Check filament calibration status

Before delivering the profile, check if the filament has been calibrated. Track calibration status in `profile_context.json` under `filament_calibration`:

```json
"filament_calibration": {
  "PLA": {
    "temperature": true,
    "max_volumetric_flow": true,
    "flow_rate": true,
    "pressure_advance": "adaptive",
    "retraction": true,
    "last_calibrated": "2026-03-06"
  }
}
```

**If the filament is NOT calibrated** (new filament):
- Generate the profile with sensible defaults from the hotend database
- Tell the user: "These are starting-point values. Before trusting this profile for real prints, run the OrcaSlicer calibration sequence for this filament."
- Present the calibration checklist (from `references/calibration_toolkit.md` "Per-Filament Calibration Checklist")
- Recommend **Adaptive PA** if the user has or will have multiple process profiles

**If the filament IS calibrated**:
- Use their calibrated values (PA, flow ratio, retraction, volumetric flow, temperature)
- Profile is ready to use immediately

**Calibration scope reminder** (critical knowledge):
- Temperature, flow rate, retraction, max volumetric flow, fan speed, min layer time, min layer speed → per-filament, ONE TIME, valid across ALL process profiles
- Pressure Advance (static) → per-filament, but varies with speed/accel. A single value is a compromise across different process profiles
- Pressure Advance (Adaptive) → per-filament, ONE TIME, valid across ALL process profiles (OrcaSlicer builds a PA model across speed/accel range)
- **Bridge flow rate → per-filament AND per-layer-height (the per-process exception)**. This is the one calibration that genuinely varies by process profile. A 0.08mm layer needs different bridge flow than 0.24mm. When generating a new process profile at a layer height the user hasn't used before, flag that bridge flow needs calibration for that layer height.
- Shrinkage compensation → per-filament, ONE TIME, valid across all process profiles. Skip for PLA/PETG (negligible). Required for ABS/ASA/Nylon/PC.
- Changing process profile (e.g., from "functional" to "miniature") does NOT require re-running filament calibration — the per-filament calibration is still valid. BUT bridge flow may need a quick re-test if the layer height changed.

### Step 6: Explain and deliver

Present the generated settings to the user with:
1. **What was set and why** — brief explanation of key choices
2. **What to watch for** — potential issues with this combo (e.g., "PETG + fast = stringing risk, monitor first layer")
3. **Calibration status** — whether this filament is calibrated or needs calibration first
4. **File location** — where the JSON was saved and how to import it

---

## Phase 3: Interactive Advisor

Beyond profile generation, answer questions about:

### Settings Explanation
"What does [setting] do?" → Explain the OrcaSlicer setting AND its Klipper equivalent.
Reference `references/orca_klipper_mapping.md` for the full mapping table.

### Calibration Guidance
"How do I calibrate [thing]?" → Provide step-by-step using OrcaSlicer built-in tools or Klipper commands.
Reference `references/calibration_toolkit.md` for the full toolkit.

### Troubleshooting
"I'm getting [problem]" → Diagnose using the known hardware profile.
Common issues: stringing, ringing/ghosting, layer adhesion, elephant foot, warping, under/over-extrusion, blobs, z-banding.

### Live Printer Query
"What are my current settings?" → Fetch live state from Moonraker API.
"Is my printer idle?" → Check `/printer/objects/query?print_stats`.

### Config Review
"Review my Klipper config" → Fetch config via Moonraker, compare against best practices for their hardware, flag issues.

---

## Scripts

### `scripts/detect_environment.sh`
Detects OS, finds OrcaSlicer binary and profile directory.
Usage: `bash scripts/detect_environment.sh`
Output: JSON to stdout with `os`, `orcaslicer_path`, `orcaslicer_version`, `profile_dir`.

### `scripts/fetch_klipper_config.sh`  
Fetches full Klipper config from Moonraker API.
Usage: `bash scripts/fetch_klipper_config.sh <moonraker_url>`
Output: JSON to stdout with parsed config sections.

### `scripts/generate_profile.py`
Generates OrcaSlicer profile JSONs from context + intent.
Usage: `python3 scripts/generate_profile.py --context state/profile_context.json --intent <intent> --filament <filament> --output-dir <dir>`
Output: OrcaSlicer-compatible JSON files.

### `scripts/install_klipper_extras.sh`
Detects and installs missing Klipper optional modules, macros, and third-party extensions.
Usage:
- Check what's missing: `bash scripts/install_klipper_extras.sh <moonraker_url> --check`
- Install extras: `bash scripts/install_klipper_extras.sh <moonraker_url> firmware_retraction exclude_object gcode_arcs kamp test_speed`
- List all available: `bash scripts/install_klipper_extras.sh <moonraker_url> --list`

Supported extras: `firmware_retraction`, `exclude_object`, `gcode_arcs`, `skew_correction`, `axis_twist_compensation`, `auto_speed`, `kamp`, `test_speed`.
Native config sections are injected via Moonraker file API. Third-party modules (auto_speed, KAMP) require SSH to the Klipper host. The script handles config injection, moonraker.conf updates, service restarts, and duplicate detection.
Output: JSON to stdout with install results per extra.

---

## References

### `references/print_intent_profiles.md`
Complete settings matrices for each print intent, with per-filament adjustments.

### `references/calibration_toolkit.md`
Full calibration workflow: what to calibrate, in what order, using what tools.

### `references/hotend_database.md`
Known hotend models with volumetric flow limits, max temps, and characteristics.

### `references/orca_klipper_mapping.md`
Complete OrcaSlicer JSON key ↔ Klipper config mapping table.

### `references/klipper_extras_database.md`
Complete reference for all optional Klipper modules/macros the skill may install. Covers native config sections, third-party modules (auto_speed, KAMP), standalone macros (TEST_SPEED), with install procedures, config snippets, and priority ordering for newbies.

---

## File Structure

```
3dprint-advisor/
├── SKILL.md                              # This file
├── AGENTS.md                             # Codebase index for AI agents
├── README.md                             # GitHub-facing documentation
├── scripts/
│   ├── detect_environment.sh             # OS + OrcaSlicer detection
│   ├── fetch_klipper_config.sh           # Moonraker API config fetch
│   ├── generate_profile.py              # Profile JSON generator
│   └── install_klipper_extras.sh        # Automated Klipper extras installer
├── references/
│   ├── print_intent_profiles.md          # Intent → settings matrices
│   ├── calibration_toolkit.md            # Calibration guide
│   ├── hotend_database.md                # Hotend flow limits
│   ├── orca_klipper_mapping.md           # Setting mapping table
│   └── klipper_extras_database.md        # Klipper module install procedures
├── state/
│   └── profile_context.json              # Persisted printer/env state (created on first run)
└── output/                               # Generated profiles land here
```
