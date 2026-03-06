# 3dprint-advisor

AI agent skill for Klipper + OrcaSlicer 3D printer setup, profile generation, calibration guidance, and Klipper extras installation. Discovers printer hardware via Moonraker API, generates intent-based slicer profiles, and acts as an interactive tuning advisor.

## Architecture

```
3dprint-advisor/
├── SKILL.md                    # Entry point — agent instructions, onboarding flow, profile generation logic
├── AGENTS.md                   # This file — codebase index for AI agents
├── README.md                   # GitHub-facing docs (install, usage, file structure)
├── LICENSE                     # MIT
├── .gitignore                  # Excludes state/*.json, output/*.json
├── scripts/                    # Executable scripts (bash + python)
│   ├── detect_environment.sh       # OS + OrcaSlicer detection
│   ├── fetch_klipper_config.sh     # Moonraker API → structured JSON
│   ├── generate_profile.py         # Intent-based OrcaSlicer profile generator
│   └── install_klipper_extras.sh   # Automated Klipper extras installer (remote via Moonraker/SSH)
├── references/                 # Static knowledge the agent reads during operation
│   ├── calibration_toolkit.md      # Full calibration workflow (627 lines)
��   ├── print_intent_profiles.md    # Intent → settings matrices (6 intents × 6 filaments)
│   ├── hotend_database.md          # 20+ hotends with flow limits, filament multipliers
│   ├── orca_klipper_mapping.md     # OrcaSlicer JSON key ↔ Klipper config mapping
│   └── klipper_extras_database.md  # Install procedures for all optional Klipper modules
├── state/                      # Runtime state (gitignored, created on first run)
│   └── profile_context.json        # Persisted printer/env/calibration state
├── output/                     # Generated profiles (gitignored)
├── knowledge/                  # Reserved for future curated knowledge
└── templates/                  # Reserved for future profile templates
```

## Key Concepts

### Discovery-Driven, Not Hardcoded
No printer details are hardcoded. First run walks the user through onboarding (SKILL.md Phase 1): detect OS/OrcaSlicer, connect to Moonraker, pull full Klipper config, ask about mods not in config (hotend model, cooling, bed surface, enclosure). Everything persists to `state/profile_context.json`.

### Intent-Based Profile Generation
Profiles are NOT generic quality tiers (fast/medium/slow). The skill asks about **print intent** before generating:
- **Functional** — brackets, mounts (accuracy + strength)
- **Visual** — display pieces (surface finish)
- **Miniature** — figurines (extreme detail, very slow)
- **Prototype** — test fits (speed, minimum quality)
- **Wearable** — TPU parts (even extrusion, no retraction artifacts)
- **Structural** — load-bearing (max layer adhesion, dense infill)

Each intent maps to different speed/accel/structure matrices in `references/print_intent_profiles.md`, then gets clamped to the user's actual hardware limits.

### Calibration Scope Model
Critical architectural decision: calibrations have different scopes that determine when they need to be redone.

| Scope | Examples | Redo When |
|-------|---------|-----------|
| **Per-printer** (one-time) | Belt tension, input shaper, skew, elephant's foot, overlap | Hardware changes |
| **Per-filament** (once per material) | Temperature, flow, PA, retraction, fan speed, min layer time | New filament |
| **Per-process** (per layer height) | Bridge flow rate | New layer height profile |

Bridge flow rate is the ONE exception that's per-process — documented throughout the codebase as a key discovery.

### Klipper Extras Auto-Installation
For newbie users with fresh Klipper installs, `scripts/install_klipper_extras.sh` can automatically install missing modules via Moonraker's file API and SSH:
- **Native config sections**: firmware_retraction, exclude_object, gcode_arcs, skew_correction, axis_twist_compensation
- **Third-party modules**: klipper_auto_speed (git clone + symlink + pip), KAMP (git clone + symlink + config)
- **Standalone macros**: TEST_SPEED (write .cfg file + include)

## File Details

### SKILL.md (330 lines) — Agent Instructions
The primary file the AI agent reads. Contains:
- **Phase 1: Onboarding** — 6-step first-run flow (detect env → ask printer → connect Moonraker → fill gaps → identify bottlenecks → save state)
- **Phase 2: Profile Generation** — Ask intent → map to settings → clamp to hardware → generate JSON → check calibration status → explain and deliver
- **Phase 3: Interactive Advisor** — Settings explanation, calibration guidance, troubleshooting, live printer query, config review
- Script documentation (usage, arguments, output format)
- File structure reference

### scripts/detect_environment.sh (159 lines)
Detects OS (macOS/Linux/Windows via WSL) and finds OrcaSlicer binary + profile directory. Outputs JSON to stdout. Tested on macOS.

### scripts/fetch_klipper_config.sh (247 lines)
Connects to Moonraker API at given URL, pulls full Klipper config (`/printer/objects/query?configfile`), and parses it into structured JSON. Extracts: printer limits, extruder settings, input shaper, firmware retraction, stepper configs, TMC driver settings, installed macros/features, and live state (current PA, accel, temps). Tested against live printer.

### scripts/generate_profile.py (642 lines)
Generates OrcaSlicer-compatible JSON profiles. Takes `--context` (profile_context.json), `--intent`, `--filament`, `--output-dir`. Contains:
- 6 intent presets × 6 filament types with full settings matrices
- Hardware clamping: speeds capped by max_velocity, accels by per-axis limits, flow by volumetric ceiling
- Outputs machine, process, filament, and machine_model JSON files with proper `inherits` chains
- Tested end-to-end, generates 13 profile files successfully.

### scripts/install_klipper_extras.sh (740 lines)
Automated installer for Klipper optional extras. Runs locally but reaches out to Moonraker API and SSH to the Klipper host. Modes: `--check` (audit what's missing), `--install` (install specified extras), `--list` (show all). Handles:
- Config section injection via Moonraker file upload API (read printer.cfg → append → upload)
- Moonraker.conf modification for update_manager entries
- SSH to Klipper host for git clone operations (auto_speed, KAMP)
- Config file creation (TEST_SPEED.cfg)
- Automatic Klipper/Moonraker restart after changes
- Duplicate detection (won't re-add existing sections)

### references/calibration_toolkit.md (627 lines)
Complete calibration workflow. Organized as:
- **Phase 1: Mechanical** — Belt tension (step 0, physical), input shaper, AUTO_SPEED, TEST_SPEED, skew correction, elephant's foot, infill/perimeter overlap
- **Scope tables** — Per-printer / per-filament / per-process breakdown with rationale
- **Phase 2: Filament** — Temperature → volumetric flow → PA → flow rate → retraction → fan speed → min layer time → min layer speed → bridge flow → shrinkage
- **Phase 3: Validation** — Tolerance, VFA, validation prints (Voron cube + Cali Dragon), hand-push temperature method
- **Per-filament checklist** — 11-step sequence with time estimates
- **Re-calibration trigger table** — What to redo after each type of change

### references/print_intent_profiles.md (133 lines)
Settings matrices for each print intent. Contains:
- Speed matrix (outer wall, inner wall, infill, top surface, travel, first layer, bridge)
- Acceleration matrix (default, outer wall, inner wall, top surface, travel, first layer)
- Structure matrix (walls, top/bottom layers, infill %, pattern, seam, ironing, bridge flow)
- Fan speed defaults by intent (min fan, max fan, bridge fan, min layer time, slow down min speed)
- Per-filament adjustments (PLA, PETG, TPU, ABS/ASA)
- Special features (ironing, Arachne, arc fitting, thin wall detection)

### references/hotend_database.md (91 lines)
20+ hotends with volumetric flow limits at 0.4mm brass/PLA baseline. Organized by category: all-metal, PTFE-lined, Volcano-style. Includes nozzle size scale factors, filament flow multipliers (PLA=1.0× through PC=0.65×), and nozzle material effects. Used by generate_profile.py and the agent to compute speed ceilings.

### references/orca_klipper_mapping.md (85 lines)
Bidirectional mapping between OrcaSlicer JSON keys and Klipper config/gcode. Covers machine settings, process speeds/accelerations, filament settings, Klipper-only features, common start gcode template, and troubleshooting table. Critical for the agent to translate between slicer concepts and firmware concepts.

### references/klipper_extras_database.md (333 lines)
Complete reference for all optional Klipper modules the skill may recommend. Four categories:
1. Native config sections (just add to printer.cfg): firmware_retraction, exclude_object, gcode_arcs, skew_correction, axis_twist_compensation, resonance_tester, input_shaper
2. Third-party modules (git clone + install): klipper_auto_speed, KAMP
3. Standalone macros (paste into config): TEST_SPEED
4. Recommendation matrix by printer type + newbie priority order

Each entry includes: what it does, detect method, install commands, config snippet, moonraker update_manager snippet.

## State Management

`state/profile_context.json` is the persistent memory across sessions. Schema (from SKILL.md):
- `environment` — OS, OrcaSlicer path/version/profile dir
- `printer` — name, kinematics, build volume, moonraker URL, hotend, extruder, nozzle, bed surface, cooling, enclosure, mods, probe
- `klipper` — max velocity/accel, input shaper, PA, firmware retraction, stealthchop, installed macros
- `bottlenecks` — Y accel limit, volumetric flow limit, speed limit reasons
- `filaments` — list of materials the user prints with
- `filament_calibration` — per-filament calibration status (temperature, flow, PA, retraction, etc.)
- `generated_profiles` — history of what's been generated

## External Dependencies

- **Moonraker API** — HTTP, no auth on LAN. Used for config fetch, file upload, service restart
- **SSH to Klipper host** — Only needed for third-party module installs (auto_speed, KAMP). Uses `pi@<host>` with key auth
- **Python 3.6+** — For generate_profile.py and JSON parsing in bash scripts
- **curl + jq** — For API calls (jq optional, python3 used as fallback)
- **OrcaSlicer** — Profile consumer. Must be on local machine or user transfers files manually

## Important Constraints

- User's OrcaSlicer is on a **separate Windows machine** — profiles must be transferred manually (no auto-push)
- No ABS/ASA profiles unless user has an enclosure
- All speeds/accels clamped to actual hardware limits (volumetric flow ceiling, per-axis accel, max velocity)
- PA varies ~33% across speed range — OrcaSlicer Adaptive PA recommended for multi-profile users
- Bridge flow rate is per-layer-height — the one calibration that IS per-process
- Zero hardcoded IPs, usernames, or printer-specific values anywhere in the codebase
