# OrcaSlicer ↔ Klipper Setting Mapping

## Machine Settings

| OrcaSlicer Key | Klipper Config | Notes |
|----------------|---------------|-------|
| `gcode_flavor` | N/A | Must be `"klipper"` |
| `machine_start_gcode` | `[gcode_macro PRINT_START]` | Call macro with params |
| `machine_end_gcode` | `[gcode_macro PRINT_END]` | Call macro |
| `nozzle_diameter` | `[extruder] nozzle_diameter` | Must match |
| `printable_area` | `[stepper_x/y] position_max` | Bed corners |
| `printable_height` | `[stepper_z] position_max` | |
| `retraction_length` | `[firmware_retraction] retract_length` | Or slicer E-moves |
| `retraction_speed` | `[firmware_retraction] retract_speed` | |
| `machine_max_speed_x/y` | `[printer] max_velocity` | Slicer uses for time estimates |
| `machine_max_acceleration_x/y` | `[printer] max_accel` | Slicer uses for time estimates |
| `machine_max_jerk_x/y` | `[printer] square_corner_velocity` | NOT Marlin jerk — SCV |

## Process Settings

### Speeds (all capped by `[printer] max_velocity`)
| OrcaSlicer Key | What It Controls |
|----------------|-----------------|
| `outer_wall_speed` | Visible surface speed — biggest quality impact |
| `inner_wall_speed` | Can be 1.5-2× outer wall |
| `sparse_infill_speed` | Internal fill — can be fastest |
| `top_surface_speed` | Visible top — keep slow for quality |
| `travel_speed` | Non-print moves — max safe speed |
| `bridge_speed` | Unsupported spans — slow for sag control |
| `initial_layer_speed` | First layer — slow for adhesion |

### Accelerations
| OrcaSlicer Key | Klipper Mechanism |
|----------------|------------------|
| `default_acceleration` | Emits `M204` → capped by `max_accel` |
| `outer_wall_acceleration` | Per-feature `M204` |
| `inner_wall_acceleration` | Per-feature `M204` |
| `top_surface_acceleration` | Per-feature `M204` |
| `travel_acceleration` | Per-feature `M204` |
| `accel_to_decel_factor` | Maps to `minimum_cruise_ratio` (50% = MCR 0.5) |

### Jerk (important gotcha)
OrcaSlicer jerk values (default_jerk, outer_wall_jerk, etc.) are used for **time estimates only** when `gcode_flavor=klipper`. Klipper uses `square_corner_velocity` instead, which is a single global value set in `[printer]`.

## Filament Settings

| OrcaSlicer Key | Klipper Mechanism |
|----------------|------------------|
| `nozzle_temperature` | `M104`/`M109` in gcode |
| `bed_temperature` | `M140`/`M190` in gcode |
| `pressure_advance` | `SET_PRESSURE_ADVANCE ADVANCE=` |
| `filament_max_volumetric_speed` | Limits effective speed (slicer-side) |
| `filament_retraction_length` | `SET_RETRACTION RETRACT_LENGTH=` if firmware retraction |
| `fan_min_speed` / `fan_max_speed` | `M106 S<0-255>` in gcode |
| `filament_flow_ratio` | `M221` in gcode |

## Klipper Features Without OrcaSlicer Equivalent

| Feature | Where | What to Know |
|---------|-------|-------------|
| `square_corner_velocity` | `[printer]` | NOT jerk — controls cornering. Default 5.0 |
| `minimum_cruise_ratio` | `[printer]` | Reduces vibration in zigzag. Default 0.5 |
| `pressure_advance_smooth_time` | `[extruder]` | Smooths PA. Default 0.04 |
| `max_extrude_cross_section` | `[extruder]` | Safety limit — increase to 5+ for wide lines |
| Input shaper | `[input_shaper]` | Auto-tune with `SHAPER_CALIBRATE` |
| Adaptive bed mesh | Start macro | `BED_MESH_CALIBRATE ADAPTIVE=1` |
| Object exclusion | `[exclude_object]` | OrcaSlicer labels objects automatically |
| Arc support | `[gcode_arcs]` | Required for `enable_arc_fitting` |
| Firmware retraction | `[firmware_retraction]` | G10/G11 — enables per-filament retraction overrides |

## Common Start G-Code Template

```
PRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]
```

## Common Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| Print time estimate way off | Machine max speed/accel in slicer ≠ Klipper config | Match values |
| "Move exceeds maximum extrusion" | `max_extrude_cross_section` too low | Set to 5+ |
| "Unknown command G2" | Missing `[gcode_arcs]` | Add section |
| PA makes extruder skip | PA × accel too high for motor torque | Lower PA or accel |
| Jerk setting does nothing | Klipper ignores Marlin jerk | Use SCV in printer.cfg |

---

## OrcaSlicer User Profile Requirements

These rules were determined by reading OrcaSlicer source (`Preset.cpp`). Violating
them causes profiles to be **silently dropped** — no error is shown in the UI.

### Required fields in every profile JSON

| Field | Required value | Notes |
|-------|---------------|-------|
| `version` | e.g. `"2.3.0.0"` | **MUST be present.** Missing = profile silently dropped on load. |
| `from` | `"User"` | Capital U. |
| `instantiation` | `"true"` | Profile won't appear in UI if missing or `"false"`. |
| `type` | `"machine"`, `"process"`, or `"filament"` | Required. |
| `name` | Unique string | Must not collide with a system profile name. |

### `inherits` — valid vs. invalid parents

OrcaSlicer only allows `inherits` to point to profiles with `instantiation: true`.
System template profiles with `instantiation: false` are stored in a separate map
and are **not findable** from user profiles.

| Profile | `instantiation` | Can be used as parent? |
|---------|----------------|----------------------|
| `fdm_klipper_common` | `false` | ❌ Silently broken |
| `fdm_process_common` | `false` | ❌ Silently broken |
| `fdm_filament_common` | Unconfirmed | ⚠️ Avoid — use `""` to be safe |
| `"MyKlipper 0.4 nozzle"` | `true` | ✅ Valid |
| `"0.20mm Standard @MyKlipper"` | `true` | ✅ Valid |
| `""` (empty string) | N/A | ✅ Standalone — no parent lookup |

**Safe fallback**: use `"inherits": ""` for all generated profiles unless you
have confirmed the named parent is `instantiation: true` in the active install.

Store the detected valid parent in `profile_context.json`:
```json
"orcaslicer_machine_parent":  "MyKlipper 0.4 nozzle",
"orcaslicer_process_parent":  "0.20mm Standard @MyKlipper",
"orcaslicer_filament_parent": ""
```

### `compatible_printers`

| Value | Effect |
|-------|--------|
| `[]` (empty array) | Profile visible for **all** printers |
| `["My Printer Name"]` | Profile visible only for that printer |
| Field omitted | Inherits parent's restriction — may hide profile unexpectedly |

Always set `"compatible_printers": []` on generated process profiles unless you
specifically want to restrict visibility.

### Logged-in account directory

When the user is signed in to OrcaSlicer, profiles live under:
```
user/<numeric_account_id>/   ← correct when logged in
user/default/                ← only used when NOT logged in
```

The active directory is whichever numeric subdirectory exists under `user/`.
`scripts/detect_environment.py` auto-detects this and returns `orcaslicer_account_id`.

### `.info` sidecar file

Every profile JSON needs a paired `.info` file when placed in a logged-in account
directory. Without it OrcaSlicer's cloud-sync purges the profile on next launch.

```
sync_info =
user_id = <account_id>
setting_id = <PREFIX><14 hex chars>
base_id = <GP004 | GM001 | GF001>
updated_time = <unix timestamp>
```

| Profile type | `setting_id` prefix | `base_id` |
|-------------|---------------------|-----------|
| Process | `PPUS` | `GP004` |
| Machine | `MPUS` | `GM001` |
| Filament | `FPUS` | `GF001` |

`scripts/generate_profile.py` writes `.info` files automatically alongside each JSON.

### Moonraker port reference

| Port | Protocol | `host_type` in machine profile |
|------|----------|-------------------------------|
| `7125` | Moonraker native API | `"klipper"` |
| `8080` | Moonraker OctoPrint compat | `"octoprint"` |
