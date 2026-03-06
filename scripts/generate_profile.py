#!/usr/bin/env python3
"""
generate_profile.py — Generate OrcaSlicer JSON profiles from printer context + print intent.

Usage:
  python3 generate_profile.py --context state/profile_context.json \
    --intent functional --filament PLA --output-dir ./output

  python3 generate_profile.py --context state/profile_context.json \
    --intent miniature --filament PLA --nozzle 0.4 --output-dir ./output

  python3 generate_profile.py --context state/profile_context.json \
    --machine-only --output-dir ./output
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ─── Intent presets ───────────────────────────────────────────────────────────
# Each intent defines base settings BEFORE hardware clamping.
# Speeds in mm/s, accels in mm/s², temps in °C, heights in mm.

INTENT_PRESETS = {
    "functional": {
        "description": "Functional parts — brackets, mounts, enclosures",
        "layer_height": 0.20,
        "initial_layer_height": 0.20,
        "wall_loops": 3,
        "top_shell_layers": 4,
        "bottom_shell_layers": 3,
        "sparse_infill_density": "25%",
        "sparse_infill_pattern": "gyroid",
        "outer_wall_speed": 80,
        "inner_wall_speed": 120,
        "sparse_infill_speed": 150,
        "internal_solid_infill_speed": 100,
        "top_surface_speed": 60,
        "bridge_speed": 25,
        "gap_infill_speed": 60,
        "travel_speed": 200,
        "initial_layer_speed": 30,
        "default_acceleration": 3000,
        "outer_wall_acceleration": 1500,
        "inner_wall_acceleration": 3000,
        "top_surface_acceleration": 1500,
        "travel_acceleration": 3000,
        "initial_layer_acceleration": 500,
        "bridge_flow": 0.95,
    },
    "visual": {
        "description": "Visual/display — vases, decorations, gifts",
        "layer_height": 0.12,
        "initial_layer_height": 0.20,
        "wall_loops": 3,
        "top_shell_layers": 5,
        "bottom_shell_layers": 4,
        "sparse_infill_density": "15%",
        "sparse_infill_pattern": "grid",
        "outer_wall_speed": 40,
        "inner_wall_speed": 60,
        "sparse_infill_speed": 80,
        "internal_solid_infill_speed": 60,
        "top_surface_speed": 30,
        "bridge_speed": 20,
        "gap_infill_speed": 30,
        "travel_speed": 150,
        "initial_layer_speed": 20,
        "default_acceleration": 1500,
        "outer_wall_acceleration": 800,
        "inner_wall_acceleration": 1500,
        "top_surface_acceleration": 800,
        "travel_acceleration": 2000,
        "initial_layer_acceleration": 500,
        "bridge_flow": 0.90,
    },
    "miniature": {
        "description": "Miniatures/figurines — fine detail, small features",
        "layer_height": 0.08,
        "initial_layer_height": 0.16,
        "wall_loops": 3,
        "top_shell_layers": 6,
        "bottom_shell_layers": 5,
        "sparse_infill_density": "15%",
        "sparse_infill_pattern": "grid",
        "outer_wall_speed": 25,
        "inner_wall_speed": 40,
        "sparse_infill_speed": 60,
        "internal_solid_infill_speed": 40,
        "top_surface_speed": 20,
        "bridge_speed": 15,
        "gap_infill_speed": 20,
        "travel_speed": 120,
        "initial_layer_speed": 15,
        "default_acceleration": 1000,
        "outer_wall_acceleration": 500,
        "inner_wall_acceleration": 1000,
        "top_surface_acceleration": 500,
        "travel_acceleration": 1500,
        "initial_layer_acceleration": 300,
        "bridge_flow": 0.85,
    },
    "prototype": {
        "description": "Prototypes/drafts — speed over quality",
        "layer_height": 0.24,
        "initial_layer_height": 0.24,
        "wall_loops": 2,
        "top_shell_layers": 3,
        "bottom_shell_layers": 3,
        "sparse_infill_density": "10%",
        "sparse_infill_pattern": "grid",
        "outer_wall_speed": 120,
        "inner_wall_speed": 180,
        "sparse_infill_speed": 200,
        "internal_solid_infill_speed": 150,
        "top_surface_speed": 80,
        "bridge_speed": 30,
        "gap_infill_speed": 80,
        "travel_speed": 250,
        "initial_layer_speed": 40,
        "default_acceleration": 5000,
        "outer_wall_acceleration": 2500,
        "inner_wall_acceleration": 5000,
        "top_surface_acceleration": 2500,
        "travel_acceleration": 5000,
        "initial_layer_acceleration": 500,
        "bridge_flow": 1.0,
    },
    "wearable": {
        "description": "Wearables/flexible — TPU-optimized",
        "layer_height": 0.20,
        "initial_layer_height": 0.24,
        "wall_loops": 4,
        "top_shell_layers": 4,
        "bottom_shell_layers": 3,
        "sparse_infill_density": "15%",
        "sparse_infill_pattern": "gyroid",
        "outer_wall_speed": 25,
        "inner_wall_speed": 30,
        "sparse_infill_speed": 40,
        "internal_solid_infill_speed": 30,
        "top_surface_speed": 20,
        "bridge_speed": 15,
        "gap_infill_speed": 20,
        "travel_speed": 80,
        "initial_layer_speed": 15,
        "default_acceleration": 1000,
        "outer_wall_acceleration": 500,
        "inner_wall_acceleration": 1000,
        "top_surface_acceleration": 500,
        "travel_acceleration": 1000,
        "initial_layer_acceleration": 300,
        "bridge_flow": 1.0,
    },
    "structural": {
        "description": "Structural/load-bearing — maximum strength",
        "layer_height": 0.20,
        "initial_layer_height": 0.24,
        "wall_loops": 5,
        "top_shell_layers": 5,
        "bottom_shell_layers": 5,
        "sparse_infill_density": "50%",
        "sparse_infill_pattern": "cubic",
        "outer_wall_speed": 60,
        "inner_wall_speed": 80,
        "sparse_infill_speed": 100,
        "internal_solid_infill_speed": 80,
        "top_surface_speed": 40,
        "bridge_speed": 20,
        "gap_infill_speed": 40,
        "travel_speed": 150,
        "initial_layer_speed": 25,
        "default_acceleration": 2000,
        "outer_wall_acceleration": 1000,
        "inner_wall_acceleration": 2000,
        "top_surface_acceleration": 1000,
        "travel_acceleration": 2000,
        "initial_layer_acceleration": 500,
        "bridge_flow": 0.95,
    },
}

# ─── Filament defaults ────────────────────────────────────────────────────────
# Base filament settings. The profile generator adjusts per-intent.

FILAMENT_DEFAULTS = {
    "PLA": {
        "nozzle_temperature": [210],
        "nozzle_temperature_initial_layer": [215],
        "bed_temperature": [60],
        "bed_temperature_initial_layer_single": [60],
        "fan_min_speed": ["100"],
        "fan_max_speed": ["100"],
        "overhang_fan_speed": ["100"],
        "close_fan_the_first_x_layers": ["1"],
        "filament_max_volumetric_speed": ["15"],
        "filament_type": ["PLA"],
        "filament_density": ["1.24"],
        "filament_cost": ["20"],
        "pressure_advance": 0.05,
        "retract_length_direct": 0.5,
        "retract_length_bowden": 4.0,
        "retract_speed": 60,
    },
    "PETG": {
        "nozzle_temperature": [235],
        "nozzle_temperature_initial_layer": [240],
        "bed_temperature": [80],
        "bed_temperature_initial_layer_single": [80],
        "fan_min_speed": ["40"],
        "fan_max_speed": ["60"],
        "overhang_fan_speed": ["80"],
        "close_fan_the_first_x_layers": ["3"],
        "filament_max_volumetric_speed": ["12"],
        "filament_type": ["PETG"],
        "filament_density": ["1.27"],
        "filament_cost": ["22"],
        "pressure_advance": 0.06,
        "retract_length_direct": 0.4,
        "retract_length_bowden": 4.5,
        "retract_speed": 40,
    },
    "TPU": {
        "nozzle_temperature": [225],
        "nozzle_temperature_initial_layer": [230],
        "bed_temperature": [50],
        "bed_temperature_initial_layer_single": [50],
        "fan_min_speed": ["60"],
        "fan_max_speed": ["80"],
        "overhang_fan_speed": ["100"],
        "close_fan_the_first_x_layers": ["3"],
        "filament_max_volumetric_speed": ["5"],
        "filament_type": ["TPU"],
        "filament_density": ["1.21"],
        "filament_cost": ["30"],
        "pressure_advance": 0.0,
        "retract_length_direct": 0.2,
        "retract_length_bowden": 0.0,  # no retraction for bowden TPU
        "retract_speed": 25,
    },
    "ABS": {
        "nozzle_temperature": [245],
        "nozzle_temperature_initial_layer": [250],
        "bed_temperature": [100],
        "bed_temperature_initial_layer_single": [100],
        "fan_min_speed": ["20"],
        "fan_max_speed": ["40"],
        "overhang_fan_speed": ["60"],
        "close_fan_the_first_x_layers": ["3"],
        "filament_max_volumetric_speed": ["12"],
        "filament_type": ["ABS"],
        "filament_density": ["1.04"],
        "filament_cost": ["22"],
        "pressure_advance": 0.05,
        "retract_length_direct": 0.4,
        "retract_length_bowden": 4.0,
        "retract_speed": 50,
    },
    "ASA": {
        "nozzle_temperature": [250],
        "nozzle_temperature_initial_layer": [255],
        "bed_temperature": [100],
        "bed_temperature_initial_layer_single": [100],
        "fan_min_speed": ["20"],
        "fan_max_speed": ["40"],
        "overhang_fan_speed": ["60"],
        "close_fan_the_first_x_layers": ["3"],
        "filament_max_volumetric_speed": ["12"],
        "filament_type": ["ASA"],
        "filament_density": ["1.07"],
        "filament_cost": ["25"],
        "pressure_advance": 0.05,
        "retract_length_direct": 0.4,
        "retract_length_bowden": 4.0,
        "retract_speed": 50,
    },
    "SILK": {
        "nozzle_temperature": [215],
        "nozzle_temperature_initial_layer": [220],
        "bed_temperature": [60],
        "bed_temperature_initial_layer_single": [60],
        "fan_min_speed": ["100"],
        "fan_max_speed": ["100"],
        "overhang_fan_speed": ["100"],
        "close_fan_the_first_x_layers": ["1"],
        "filament_max_volumetric_speed": ["12"],
        "filament_type": ["PLA"],
        "filament_density": ["1.24"],
        "filament_cost": ["25"],
        "pressure_advance": 0.04,
        "retract_length_direct": 0.5,
        "retract_length_bowden": 4.0,
        "retract_speed": 60,
    },
}


def load_context(path):
    with open(path) as f:
        return json.load(f)


def clamp_speed(speed, max_velocity, volumetric_limit, layer_height, line_width):
    """Clamp speed to hardware limits."""
    # Cap by max velocity
    speed = min(speed, max_velocity)
    # Cap by volumetric flow: flow = layer_h * line_w * speed
    if volumetric_limit and layer_height and line_width:
        max_speed_by_flow = volumetric_limit / (layer_height * line_width)
        speed = min(speed, max_speed_by_flow)
    return round(speed)


def clamp_accel(accel, max_accel, y_accel_limit=None):
    """Clamp acceleration to hardware limits."""
    accel = min(accel, max_accel)
    if y_accel_limit:
        accel = min(accel, y_accel_limit)
    return round(accel)


def generate_machine_profile(ctx, output_dir):
    """Generate machine (printer) profile JSON."""
    printer = ctx.get("printer", {})
    klipper = ctx.get("klipper", {})
    env = ctx.get("environment", {})
    build = ctx.get("printer", {}).get(
        "build_volume", ctx.get("klipper", {}).get("build_volume", {})
    )

    nozzle = printer.get("nozzle", {}).get("diameter", 0.4)
    name = printer.get("name", "My Klipper Printer")
    safe_name = name.replace(" ", "_").replace("/", "_")

    # Build printable area from build volume
    x_max = build.get("x", build.get("x_max", 235))
    y_max = build.get("y", build.get("y_max", 235))
    z_max = build.get("z", build.get("z_max", 250))

    max_vel = klipper.get("max_velocity", 300)
    max_accel = klipper.get("max_accel", 3000)

    # Firmware retraction settings from klipper
    fw_ret = klipper.get("firmware_retraction", {})
    retract_length = fw_ret.get("length", fw_ret.get("retract_length", 0.5))
    retract_speed = fw_ret.get("speed", fw_ret.get("retract_speed", 60))
    unretract_speed = fw_ret.get("unretract_speed", 60)

    profile = {
        "type": "machine",
        "name": f"{name} {nozzle}mm nozzle",
        "from": "User",
        "instantiation": "true",
        "inherits": "fdm_klipper_common",
        "gcode_flavor": "klipper",
        "nozzle_diameter": [str(nozzle)],
        "printer_model": safe_name,
        "printer_variant": f"{nozzle}",
        "printable_area": [f"0x0", f"{x_max}x0", f"{x_max}x{y_max}", f"0x{y_max}"],
        "printable_height": str(z_max),
        "machine_max_speed_x": [str(max_vel)],
        "machine_max_speed_y": [str(max_vel)],
        "machine_max_speed_z": [str(klipper.get("max_z_velocity", 15))],
        "machine_max_speed_e": ["60"],
        "machine_max_acceleration_x": [str(max_accel)],
        "machine_max_acceleration_y": [str(max_accel)],
        "machine_max_acceleration_z": [str(klipper.get("max_z_accel", 100))],
        "machine_max_acceleration_e": ["5000"],
        "machine_max_jerk_x": ["9"],
        "machine_max_jerk_y": ["9"],
        "machine_max_jerk_z": ["3"],
        "machine_max_jerk_e": ["2.5"],
        "retraction_length": [str(retract_length)],
        "retraction_speed": [str(int(retract_speed))],
        "deretraction_speed": [str(int(unretract_speed))],
        "retract_before_wipe": ["70%"],
        "retraction_minimum_travel": ["1"],
        "z_hop": ["0.4"],
        "z_hop_types": ["Auto Lift"],
        "machine_start_gcode": f"PRINT_START EXTRUDER=[nozzle_temperature_initial_layer] BED=[bed_temperature_initial_layer_single]",
        "machine_end_gcode": "PRINT_END",
        "before_layer_change_gcode": ";BEFORE_LAYER_CHANGE\\n;[layer_z]\\nG92 E0",
        "layer_change_gcode": ";AFTER_LAYER_CHANGE\\n;[layer_z]",
        "change_filament_gcode": "M600",
        "machine_pause_gcode": "PAUSE",
    }

    filename = f"{safe_name}_{nozzle}mm_nozzle.json"
    filepath = os.path.join(output_dir, "machine", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2)

    return filepath, profile["name"]


def generate_process_profile(ctx, intent, output_dir):
    """Generate process (print settings) profile JSON."""
    if intent not in INTENT_PRESETS:
        print(
            f"ERROR: Unknown intent '{intent}'. Available: {list(INTENT_PRESETS.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    preset = INTENT_PRESETS[intent]
    printer = ctx.get("printer", {})
    klipper = ctx.get("klipper", {})
    bottlenecks = ctx.get("bottlenecks", {})

    nozzle = printer.get("nozzle", {}).get("diameter", 0.4)
    max_vel = klipper.get("max_velocity", 300)
    max_accel = klipper.get("max_accel", 3000)
    y_accel_limit = bottlenecks.get("y_accel_limit")
    vol_flow_limit = bottlenecks.get("volumetric_flow_limit")
    name = printer.get("name", "My Klipper Printer")
    safe_name = name.replace(" ", "_").replace("/", "_")

    layer_h = preset["layer_height"]
    line_width = round(nozzle * 1.1, 3)  # Standard: 110% of nozzle

    # Clamp all speeds
    def cs(speed):
        return clamp_speed(speed, max_vel, vol_flow_limit, layer_h, line_width)

    def ca(accel):
        return clamp_accel(accel, max_accel, y_accel_limit)

    profile = {
        "type": "process",
        "name": f"{layer_h}mm {intent.capitalize()} @{safe_name}",
        "from": "User",
        "instantiation": "true",
        "inherits": "fdm_process_common",
        "layer_height": str(layer_h),
        "initial_layer_print_height": str(preset["initial_layer_height"]),
        "line_width": str(line_width),
        "initial_layer_line_width": str(round(nozzle * 1.2, 3)),
        "wall_loops": str(preset["wall_loops"]),
        "top_shell_layers": str(preset["top_shell_layers"]),
        "bottom_shell_layers": str(preset["bottom_shell_layers"]),
        "sparse_infill_density": preset["sparse_infill_density"],
        "sparse_infill_pattern": preset["sparse_infill_pattern"],
        "outer_wall_speed": str(cs(preset["outer_wall_speed"])),
        "inner_wall_speed": str(cs(preset["inner_wall_speed"])),
        "sparse_infill_speed": str(cs(preset["sparse_infill_speed"])),
        "internal_solid_infill_speed": str(cs(preset["internal_solid_infill_speed"])),
        "top_surface_speed": str(cs(preset["top_surface_speed"])),
        "bridge_speed": str(cs(preset["bridge_speed"])),
        "gap_infill_speed": str(cs(preset["gap_infill_speed"])),
        "travel_speed": str(cs(preset["travel_speed"])),
        "initial_layer_speed": str(cs(preset["initial_layer_speed"])),
        "default_acceleration": str(ca(preset["default_acceleration"])),
        "outer_wall_acceleration": str(ca(preset["outer_wall_acceleration"])),
        "inner_wall_acceleration": str(ca(preset["inner_wall_acceleration"])),
        "top_surface_acceleration": str(ca(preset["top_surface_acceleration"])),
        "travel_acceleration": str(ca(preset["travel_acceleration"])),
        "initial_layer_acceleration": str(ca(preset["initial_layer_acceleration"])),
        "bridge_flow": str(preset["bridge_flow"]),
        "seam_position": "aligned" if intent in ("visual", "miniature") else "nearest",
        "enable_arc_fitting": "1",
        "wall_generator": "arachne",
        "detect_thin_wall": "1",
        "only_one_wall_top": "1" if intent in ("miniature", "visual") else "0",
        "ironing_type": "top" if intent == "miniature" else "no ironing",
    }

    # Miniature-specific: enable ironing for top surfaces
    if intent == "miniature":
        profile["ironing_speed"] = "15"
        profile["ironing_flow"] = "10%"

    filename = f"{layer_h}mm_{intent}_{safe_name}.json"
    filepath = os.path.join(output_dir, "process", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2)

    return filepath, profile["name"]


def generate_filament_profile(ctx, filament, output_dir):
    """Generate filament profile JSON."""
    filament_upper = filament.upper()
    if filament_upper not in FILAMENT_DEFAULTS:
        print(
            f"ERROR: Unknown filament '{filament}'. Available: {list(FILAMENT_DEFAULTS.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    defaults = FILAMENT_DEFAULTS[filament_upper]
    printer = ctx.get("printer", {})
    klipper = ctx.get("klipper", {})
    bottlenecks = ctx.get("bottlenecks", {})

    name = printer.get("name", "My Klipper Printer")
    safe_name = name.replace(" ", "_").replace("/", "_")
    extruder_type = printer.get("extruder", {}).get("type", "direct")
    is_direct = extruder_type.lower() in ("direct", "direct drive", "direct_drive")

    # Pick retraction based on extruder type
    retract_len = (
        defaults["retract_length_direct"]
        if is_direct
        else defaults["retract_length_bowden"]
    )

    # Cap volumetric flow to hardware limit
    hw_flow_limit = bottlenecks.get("volumetric_flow_limit")
    filament_flow = float(defaults["filament_max_volumetric_speed"][0])
    if hw_flow_limit:
        filament_flow = min(filament_flow, hw_flow_limit)

    # Use PA from klipper config if available, else filament default
    pa = klipper.get("pressure_advance", defaults["pressure_advance"])

    profile = {
        "type": "filament",
        "name": f"{filament_upper} @{safe_name}",
        "from": "User",
        "instantiation": "true",
        "inherits": "fdm_filament_common",
        "filament_type": defaults["filament_type"],
        "nozzle_temperature": [str(t) for t in defaults["nozzle_temperature"]],
        "nozzle_temperature_initial_layer": [
            str(t) for t in defaults["nozzle_temperature_initial_layer"]
        ],
        "bed_temperature": [str(t) for t in defaults["bed_temperature"]],
        "bed_temperature_initial_layer_single": [
            str(t) for t in defaults["bed_temperature_initial_layer_single"]
        ],
        "fan_min_speed": defaults["fan_min_speed"],
        "fan_max_speed": defaults["fan_max_speed"],
        "overhang_fan_speed": defaults["overhang_fan_speed"],
        "close_fan_the_first_x_layers": defaults["close_fan_the_first_x_layers"],
        "filament_max_volumetric_speed": [str(filament_flow)],
        "filament_density": defaults["filament_density"],
        "filament_cost": defaults["filament_cost"],
        "pressure_advance": [str(pa)],
        "filament_retraction_length": [str(retract_len)] if retract_len else None,
        "filament_retraction_speed": [str(defaults["retract_speed"])],
        "filament_deretraction_speed": [str(defaults["retract_speed"])],
    }

    # Remove None values
    profile = {k: v for k, v in profile.items() if v is not None}

    filename = f"{filament_upper}_{safe_name}.json"
    filepath = os.path.join(output_dir, "filament", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2)

    return filepath, profile["name"]


def main():
    parser = argparse.ArgumentParser(description="Generate OrcaSlicer profiles")
    parser.add_argument("--context", required=True, help="Path to profile_context.json")
    parser.add_argument(
        "--intent", choices=list(INTENT_PRESETS.keys()), help="Print intent"
    )
    parser.add_argument(
        "--filament", help="Filament type (PLA, PETG, TPU, ABS, ASA, SILK)"
    )
    parser.add_argument("--output-dir", default="./output", help="Output directory")
    parser.add_argument(
        "--machine-only", action="store_true", help="Only generate machine profile"
    )
    parser.add_argument(
        "--all-intents", action="store_true", help="Generate all intent profiles"
    )
    parser.add_argument(
        "--all-filaments", action="store_true", help="Generate all filament profiles"
    )
    parser.add_argument(
        "--list-intents", action="store_true", help="List available intents"
    )
    parser.add_argument(
        "--list-filaments", action="store_true", help="List available filaments"
    )
    args = parser.parse_args()

    if args.list_intents:
        for k, v in INTENT_PRESETS.items():
            print(f"  {k:15s} — {v['description']}")
        return

    if args.list_filaments:
        for k, v in FILAMENT_DEFAULTS.items():
            temps = v["nozzle_temperature"][0]
            flow = v["filament_max_volumetric_speed"][0]
            print(f"  {k:8s} — {temps}°C nozzle, {flow} mm³/s max flow")
        return

    ctx = load_context(args.context)
    output_dir = args.output_dir
    generated = []

    # Always generate machine profile
    path, name = generate_machine_profile(ctx, output_dir)
    generated.append({"type": "machine", "name": name, "path": path})
    print(f"  Machine: {path}", file=sys.stderr)

    if args.machine_only:
        print(json.dumps(generated, indent=2))
        return

    # Process profiles
    intents = (
        list(INTENT_PRESETS.keys())
        if args.all_intents
        else ([args.intent] if args.intent else [])
    )
    for intent in intents:
        path, name = generate_process_profile(ctx, intent, output_dir)
        generated.append({"type": "process", "name": name, "path": path})
        print(f"  Process: {path}", file=sys.stderr)

    # Filament profiles
    if args.all_filaments:
        filaments = list(FILAMENT_DEFAULTS.keys())
    elif args.filament:
        filaments = [f.strip() for f in args.filament.split(",")]
    else:
        filaments = []

    for filament in filaments:
        path, name = generate_filament_profile(ctx, filament, output_dir)
        generated.append({"type": "filament", "name": name, "path": path})
        print(f"  Filament: {path}", file=sys.stderr)

    # Output summary
    print(json.dumps(generated, indent=2))


if __name__ == "__main__":
    main()
