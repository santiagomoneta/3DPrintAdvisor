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
│   ├── fetch_klipper_config.sh     # Moonraker API → structured JSON (full config parse)
│   ├── fetch_config.sh             # Fetch a single config file by name
│   ├── upload_config.sh            # Upload config file via Moonraker
│   ├── send_gcode.sh               # Send G-code command to Klipper
│   ├── query_status.sh             # Query live printer state
│   ├── diagnose.sh                 # Full config diagnostic report
│   ├── generate_profile.py         # Intent-based OrcaSlicer profile generator
│   └── install_klipper_extras.sh   # Automated Klipper extras installer (remote via Moonraker/SSH)
├── references/                 # Static knowledge the agent reads during operation
│   ├── calibration_toolkit.md      # Full calibration workflow (627 lines)
│   ├── print_intent_profiles.md    # Intent → settings matrices (6 intents × 6 filaments)
│   ├── hotend_database.md          # 20+ hotends with flow limits, filament multipliers
│   ├── orca_klipper_mapping.md     # OrcaSlicer JSON key ↔ Klipper config mapping
│   ├── klipper_extras_database.md  # Install procedures for all optional Klipper modules
│   ├── config_sections.md          # All 40+ Klipper config sections + parameters
│   ├── gcodes.md                   # G-code and extended Klipper command reference
│   ├── moonraker_api.md            # Moonraker REST API with curl examples
│   ├── troubleshooting.md          # 20+ error patterns with root causes and fixes
│   ├── placeholders.md             # OrcaSlicer built-in placeholder variable reference
│   ├── profiles.md                 # OrcaSlicer profile JSON schema + inheritance model
│   └── settings.md                 # Annotated OrcaSlicer settings reference
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

### scripts/detect_environment.sh
Bash wrapper. Detects OS (macOS/Linux/Windows via WSL) and finds OrcaSlicer binary + profile directory.

### scripts/detect_environment.py
Python implementation (cross-platform). Outputs JSON to stdout with fields:
`os`, `orcaslicer_path`, `orcaslicer_found`, `orcaslicer_version`, `orcaslicer_profile_dir`,
`orcaslicer_profile_dir_exists`, `orcaslicer_account_id`.
Scans `user/` for numeric subdirectories (logged-in account IDs) and prefers them over `default`.

### scripts/fetch_klipper_config.sh (247 lines)
Connects to Moonraker API at given URL, pulls full Klipper config (`/printer/objects/query?configfile`), and parses it into structured JSON. Extracts: printer limits, extruder settings, input shaper, firmware retraction, stepper configs, TMC driver settings, installed macros/features, and live state (current PA, accel, temps). Tested against live printer.

### scripts/generate_profile.py
Generates OrcaSlicer-compatible JSON profiles. Takes `--context` (profile_context.json), `--intent`, `--filament`, `--output-dir`. Contains:
- 6 intent presets × 6 filament types with full settings matrices
- Hardware clamping: speeds capped by max_velocity, accels by per-axis limits, flow by volumetric ceiling
- Outputs machine, process, and filament JSON files with proper `version`, `inherits`, `compatible_printers`
- Writes paired `.info` sidecar files for logged-in account directories
- `inherits` parents read from `profile_context.json` (`orcaslicer_machine/process/filament_parent`); defaults to `""` (standalone)

### scripts/install_klipper_extras.sh (740 lines)
Automated installer for Klipper optional extras. Runs locally but reaches out to Moonraker API and SSH to the Klipper host. Modes: `--check` (audit what's missing), `--install` (install specified extras), `--list` (show all). Handles:
- Config section injection via Moonraker file upload API (read printer.cfg → append → upload)
- Moonraker.conf modification for update_manager entries
- SSH to Klipper host for git clone operations (auto_speed, KAMP)
- Config file creation (TEST_SPEED.cfg)
- Automatic Klipper/Moonraker restart after changes
- Duplicate detection (won't re-add existing sections)

### scripts/fetch_config.sh
Fetches a specific config file by name from Moonraker (`/server/files/config/<filename>`). Useful for reading individual files (e.g. `macros/macros.cfg`) without pulling the entire config.

### scripts/upload_config.sh
Uploads a local file to Klipper via Moonraker's file upload API. Correctly uses `filename=` form field (not `path=`) to avoid Moonraker `NotADirectoryError`. Supports subdirectory targets via optional third argument.

### scripts/send_gcode.sh
Sends a single G-code command to Klipper via `POST /printer/gcode/script`. Use for `FIRMWARE_RESTART`, `SAVE_CONFIG`, `BED_MESH_CALIBRATE`, and any other G-code commands.

### scripts/query_status.sh
Queries live printer state via `GET /printer/objects/query`. Returns temperatures, print status, toolhead position, current accel/velocity, and motion state.

### scripts/diagnose.sh
Runs a full diagnostic pass against the live printer: fetches all config files, checks for duplicate sections, deprecated parameters, out-of-range values, and common misconfigurations. Outputs a human-readable report.

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

### references/config_sections.md
All 40+ Klipper config section types with their full parameter list, required fields, valid value ranges, and notes. Use when reviewing printer.cfg, diagnosing config errors, or generating new config sections.

### references/gcodes.md
Complete reference for all standard G-codes (G0, G1, G28, M104, etc.) and Klipper extended commands (SHAPER_CALIBRATE, BED_MESH_CALIBRATE, PRESSURE_ADVANCE_CALIBRATE, SAVE_CONFIG, etc.). Includes arguments, examples, and notes on Klipper-specific behavior.

### references/moonraker_api.md
Full Moonraker REST API reference with curl examples. Covers: `/printer/objects/query`, `/printer/gcode/script`, `/server/files/upload` (with correct form fields), `/printer/firmware_restart`, `/server/files/list`, and more. Critical for building correct API calls without guessing form field names.

### references/troubleshooting.md
20+ common Klipper error patterns (regex-matchable) with root cause analysis and precise fix steps. Covers: move out of range, duplicate sections, deprecated parameters, TMC UART errors, BLTouch failures, extruder max extrude errors, and more.

### references/placeholders.md
Complete reference for all OrcaSlicer built-in placeholder variables available in start/end G-code, layer change G-code, and toolchange G-code. Includes variable names, types, and example usage.

### references/profiles.md
OrcaSlicer profile JSON schema covering all four profile types (machine, process, filament, vendor). Documents required fields, `inherits` resolution rules, `.info` sidecar format, `compatible_printers` behavior, and common pitfalls from Preset.cpp source analysis.

### references/settings.md
Annotated reference for all major OrcaSlicer settings across the three profile types. Each entry includes the config key name (also usable as a placeholder), a description of what it controls, valid range, and effect on print quality. Covers speed, acceleration, quality, support, infill, retraction, and cooling settings.

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

## OrcaSlicer Profile Loading Rules (from Preset.cpp source analysis)

These rules were reverse-engineered from OrcaSlicer source. Violating them causes
profiles to be **silently dropped** with no UI error.

### Required JSON fields
Every profile must have:
- `"version"` — e.g. `"2.3.0.0"`. **Missing = silently dropped.**
- `"from": "User"` — capital U
- `"instantiation": "true"` — profile won't show in UI without this
- `"type"` — `"machine"`, `"process"`, or `"filament"`

### `inherits` — broken parents
OrcaSlicer only resolves `inherits` against profiles with `instantiation: true`.
System templates (`fdm_klipper_common`, `fdm_process_common`, `fdm_filament_common`)
all have `instantiation: false` — they are stored in a separate config_maps dict
and are **not findable** from user profiles.

**Rule**: generated profiles use `"inherits": ""` (standalone) by default.
If a valid instantiated parent is detected during onboarding, store it in
`profile_context.json` as:
```json
"orcaslicer_machine_parent":  "MyKlipper 0.4 nozzle",
"orcaslicer_process_parent":  "0.20mm Standard @MyKlipper",
"orcaslicer_filament_parent": ""
```

### `compatible_printers`
- `[]` (empty array) = visible for all printers — always set this on process profiles
- Omitting the field = inherits parent's restriction, which may hide the profile

### Logged-in account directory
When the user is signed in, OrcaSlicer uses `user/<account_id>/`, NOT `user/default/`.
`detect_environment.py` now auto-detects this by scanning for numeric subdirectories.
The `orcaslicer_account_id` field is added to the output JSON.

### `.info` sidecar files
Every profile JSON in a logged-in account directory needs a `.info` file:
```
sync_info =
user_id = <account_id>
setting_id = <PREFIX><14 hex chars>   # PPUS=process, MPUS=machine, FPUS=filament
base_id = <GP004 | GM001 | GF001>
updated_time = <unix timestamp>
```
`generate_profile.py` writes these automatically. Profiles without `.info` are
purged by cloud-sync on next OrcaSlicer launch.
