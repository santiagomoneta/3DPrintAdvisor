#!/usr/bin/env bash
# fetch_klipper_config.sh — Fetch full Klipper config from Moonraker API
# Usage: bash fetch_klipper_config.sh <moonraker_url>
# Output: JSON to stdout with parsed config sections + live state
# Exit codes: 0=success, 1=connectivity error, 2=klipper not ready

set -euo pipefail

MOONRAKER_URL="${1:?Usage: fetch_klipper_config.sh <moonraker_url>}"
# Strip trailing slash
MOONRAKER_URL="${MOONRAKER_URL%/}"
TIMEOUT=5

log() { echo "$@" >&2; }

# Test connectivity
test_connection() {
  local response
  response=$(curl -s --connect-timeout "$TIMEOUT" "${MOONRAKER_URL}/server/info" 2>&1) || {
    log "ERROR: Cannot reach Moonraker at ${MOONRAKER_URL}"
    exit 1
  }
  
  local klippy_state
  klippy_state=$(echo "$response" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['klippy_state'])" 2>/dev/null) || {
    log "ERROR: Unexpected response from Moonraker"
    exit 1
  }

  if [ "$klippy_state" != "ready" ]; then
    log "WARNING: Klipper state is '$klippy_state' (not ready). Config may be incomplete."
  fi

  echo "$response"
}

# Fetch config file object (contains all parsed config sections)
fetch_config() {
  curl -s --connect-timeout "$TIMEOUT" \
    "${MOONRAKER_URL}/printer/objects/query?configfile" 2>/dev/null
}

# Fetch live printer state
fetch_state() {
  curl -s --connect-timeout "$TIMEOUT" \
    "${MOONRAKER_URL}/printer/objects/query?extruder&toolhead&input_shaper&print_stats&heater_bed&fan" 2>/dev/null
}

# Fetch printer info (hostname, software versions)
fetch_printer_info() {
  curl -s --connect-timeout "$TIMEOUT" \
    "${MOONRAKER_URL}/printer/info" 2>/dev/null
}

# Main — combine all into a single JSON output
main() {
  local server_info config_data state_data printer_info

  log "Connecting to Moonraker at ${MOONRAKER_URL}..."
  server_info=$(test_connection)

  log "Fetching Klipper config..."
  config_data=$(fetch_config)

  log "Fetching live state..."
  state_data=$(fetch_state)

  log "Fetching printer info..."
  printer_info=$(fetch_printer_info)

  # Combine and parse with Python (available on any system running this)
  python3 <<'PYEOF' - "$server_info" "$config_data" "$state_data" "$printer_info"
import json, sys

server_info = json.loads(sys.argv[1])
config_data = json.loads(sys.argv[2])
state_data = json.loads(sys.argv[3])
printer_info = json.loads(sys.argv[4])

config = config_data.get("result", {}).get("status", {}).get("configfile", {}).get("config", {})
state = state_data.get("result", {}).get("status", {})

# Extract key config sections
def get_section(name):
    return config.get(name, {})

def get_float(section, key, default=None):
    val = get_section(section).get(key)
    if val is not None:
        try:
            return float(val)
        except (ValueError, TypeError):
            pass
    return default

def get_str(section, key, default=""):
    return get_section(section).get(key, default)

def get_bool(section, key, default=False):
    val = get_section(section).get(key, str(default))
    return str(val).lower() in ("true", "1", "yes")

# Build structured output
output = {
    "moonraker_version": server_info.get("result", {}).get("moonraker_version", ""),
    "klippy_state": server_info.get("result", {}).get("klippy_state", ""),
    "components": server_info.get("result", {}).get("components", []),
    "warnings": server_info.get("result", {}).get("warnings", []),

    "printer": {
        "kinematics": get_str("printer", "kinematics"),
        "max_velocity": get_float("printer", "max_velocity"),
        "max_accel": get_float("printer", "max_accel"),
        "max_z_velocity": get_float("printer", "max_z_velocity"),
        "max_z_accel": get_float("printer", "max_z_accel"),
        "square_corner_velocity": get_float("printer", "square_corner_velocity", 5.0),
        "minimum_cruise_ratio": get_float("printer", "minimum_cruise_ratio"),
    },

    "build_volume": {
        "x_max": get_float("stepper_x", "position_max"),
        "y_max": get_float("stepper_y", "position_max"),
        "z_max": get_float("stepper_z", "position_max"),
        "x_min": get_float("stepper_x", "position_min", 0),
        "y_min": get_float("stepper_y", "position_min", 0),
    },

    "extruder": {
        "rotation_distance": get_float("extruder", "rotation_distance"),
        "nozzle_diameter": get_float("extruder", "nozzle_diameter"),
        "filament_diameter": get_float("extruder", "filament_diameter"),
        "max_extrude_cross_section": get_float("extruder", "max_extrude_cross_section"),
        "max_extrude_only_distance": get_float("extruder", "max_extrude_only_distance"),
        "max_temp": get_float("extruder", "max_temp"),
        "sensor_type": get_str("extruder", "sensor_type"),
        "pressure_advance": get_float("extruder", "pressure_advance"),
        "pressure_advance_smooth_time": get_float("extruder", "pressure_advance_smooth_time"),
    },

    "input_shaper": {
        "shaper_type_x": get_str("input_shaper", "shaper_type_x"),
        "shaper_freq_x": get_float("input_shaper", "shaper_freq_x"),
        "shaper_type_y": get_str("input_shaper", "shaper_type_y"),
        "shaper_freq_y": get_float("input_shaper", "shaper_freq_y"),
    },

    "firmware_retraction": {
        "retract_length": get_float("firmware_retraction", "retract_length"),
        "retract_speed": get_float("firmware_retraction", "retract_speed"),
        "unretract_extra_length": get_float("firmware_retraction", "unretract_extra_length"),
        "unretract_speed": get_float("firmware_retraction", "unretract_speed"),
    } if "firmware_retraction" in config else None,

    "tmc_drivers": {},
    "bed": {
        "max_temp": get_float("heater_bed", "max_temp"),
        "sensor_type": get_str("heater_bed", "sensor_type"),
    },

    "bed_mesh": {
        "mesh_min": get_str("bed_mesh", "mesh_min"),
        "mesh_max": get_str("bed_mesh", "mesh_max"),
        "probe_count": get_str("bed_mesh", "probe_count"),
    } if "bed_mesh" in config else None,

    "probe": {},

    "installed_features": {
        "exclude_object": "exclude_object" in config,
        "gcode_arcs": "gcode_arcs" in config,
        "firmware_retraction": "firmware_retraction" in config,
        "skew_correction": "skew_correction" in config,
        "axis_twist_compensation": "axis_twist_compensation" in config,
        "resonance_tester": "resonance_tester" in config,
        "auto_speed": "auto_speed" in config,
    },

    "installed_macros": [],

    "live_state": {
        "extruder_temp": state.get("extruder", {}).get("temperature"),
        "extruder_target": state.get("extruder", {}).get("target"),
        "pressure_advance": state.get("extruder", {}).get("pressure_advance"),
        "pressure_advance_smooth_time": state.get("extruder", {}).get("smooth_time"),
        "bed_temp": state.get("heater_bed", {}).get("temperature"),
        "bed_target": state.get("heater_bed", {}).get("target"),
        "toolhead_max_velocity": state.get("toolhead", {}).get("max_velocity"),
        "toolhead_max_accel": state.get("toolhead", {}).get("max_accel"),
        "toolhead_scv": state.get("toolhead", {}).get("square_corner_velocity"),
        "toolhead_mcr": state.get("toolhead", {}).get("minimum_cruise_ratio"),
        "homed_axes": state.get("toolhead", {}).get("homed_axes"),
        "print_state": state.get("print_stats", {}).get("state"),
        "print_filename": state.get("print_stats", {}).get("filename"),
        "fan_speed": state.get("fan", {}).get("speed"),
    },
}

# TMC drivers
for axis in ["stepper_x", "stepper_y", "stepper_z", "extruder"]:
    tmc_section = f"tmc2209 {axis}"
    if tmc_section not in config:
        tmc_section = f"tmc2208 {axis}"
    if tmc_section not in config:
        tmc_section = f"tmc5160 {axis}"
    if tmc_section in config:
        output["tmc_drivers"][axis] = {
            "driver": tmc_section.split(" ")[0],
            "run_current": get_float(tmc_section.split(" ")[0] + " " + axis, "run_current"),
            "hold_current": get_float(tmc_section.split(" ")[0] + " " + axis, "hold_current"),
            "stealthchop_threshold": get_float(tmc_section.split(" ")[0] + " " + axis, "stealthchop_threshold"),
            "interpolate": get_bool(tmc_section.split(" ")[0] + " " + axis, "interpolate"),
        }

# Probe info
for probe_type in ["bltouch", "probe", "probe_eddy_current", "beacon"]:
    if probe_type in config:
        output["probe"] = {
            "type": probe_type,
            "z_offset": get_float(probe_type, "z_offset"),
        }
        break

# Detect installed macros (look for gcode_macro sections)
known_macros = [
    "PRINT_START", "PRINT_END", "PAUSE", "RESUME", "CANCEL_PRINT",
    "M600", "LOAD_FILAMENT", "UNLOAD_FILAMENT",
    "TEST_SPEED", "BED_MESH_CALIBRATE", "LINE_PURGE", "VORON_PURGE", "SMART_PARK",
    "RESET_TO_DEFAULTS", "SAFE_Z_RAISE", "CREATE_MESH",
]
for macro in known_macros:
    key = f"gcode_macro {macro}"
    if key in config or key.lower() in [k.lower() for k in config]:
        output["installed_macros"].append(macro)

# Check for KAMP
if "gcode_macro _KAMP_Settings" in config or "gcode_macro _kamp_settings" in [k.lower() for k in config]:
    output["installed_macros"].append("KAMP")

# Check for auto_speed
if "auto_speed" in config:
    output["installed_macros"].append("AUTO_SPEED")

print(json.dumps(output, indent=2))
PYEOF
}

main
