import json
import sys
import urllib.request
import urllib.error
import time

def fetch_url(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"ERROR: Failed to fetch {url}: {e}", file=sys.stderr)
        return None

def get_config(moonraker_url):
    moonraker_url = moonraker_url.rstrip('/')
    
    print(f"Connecting to Moonraker at {moonraker_url}...", file=sys.stderr)
    server_info = fetch_url(f"{moonraker_url}/server/info")
    if not server_info:
        sys.exit(1)

    klippy_state = server_info.get("result", {}).get("klippy_state")
    if klippy_state != "ready":
        print(f"WARNING: Klipper state is '{klippy_state}' (not ready).", file=sys.stderr)

    print("Fetching Klipper config and state...", file=sys.stderr)
    config_data = fetch_url(f"{moonraker_url}/printer/objects/query?configfile")
    state_data = fetch_url(f"{moonraker_url}/printer/objects/query?extruder&toolhead&input_shaper&print_stats&heater_bed&fan")
    printer_info = fetch_url(f"{moonraker_url}/printer/info")

    config = config_data.get("result", {}).get("status", {}).get("configfile", {}).get("config", {})
    state = state_data.get("result", {}).get("status", {})

    # Helper functions for parsing
    def get_section(name): return config.get(name, {})
    def get_float(section, key, default=None):
        val = get_section(section).get(key)
        try: return float(val) if val is not None else default
        except: return default
    def get_str(section, key, default=""): return str(get_section(section).get(key, default))
    def get_bool(section, key, default=False):
        val = str(get_section(section).get(key, default)).lower()
        return val in ("true", "1", "yes")

    # Build the structured output (same schema as before)
    output = {
        "moonraker_version": server_info.get("result", {}).get("moonraker_version", ""),
        "klippy_state": klippy_state,
        "printer": {
            "kinematics": get_str("printer", "kinematics"),
            "max_velocity": get_float("printer", "max_velocity"),
            "max_accel": get_float("printer", "max_accel"),
        },
        "build_volume": {
            "x_max": get_float("stepper_x", "position_max"),
            "y_max": get_float("stepper_y", "position_max"),
            "z_max": get_float("stepper_z", "position_max"),
        },
        "extruder": {
            "rotation_distance": get_float("extruder", "rotation_distance"),
            "nozzle_diameter": get_float("extruder", "nozzle_diameter"),
            "max_temp": get_float("extruder", "max_temp"),
            "pressure_advance": get_float("extruder", "pressure_advance"),
        },
        "input_shaper": {
            "shaper_type_x": get_str("input_shaper", "shaper_type_x"),
            "shaper_freq_x": get_float("input_shaper", "shaper_freq_x"),
            "shaper_type_y": get_str("input_shaper", "shaper_type_y"),
            "shaper_freq_y": get_float("input_shaper", "shaper_freq_y"),
        },
        "installed_features": {
            "exclude_object": "exclude_object" in config,
            "gcode_arcs": "gcode_arcs" in config,
            "firmware_retraction": "firmware_retraction" in config,
        },
        "installed_macros": []
    }

    # Detect macros
    known_macros = ["PRINT_START", "PRINT_END", "PAUSE", "RESUME", "TEST_SPEED", "KAMP", "AUTO_SPEED"]
    for macro in known_macros:
        if f"gcode_macro {macro}" in config or f"gcode_macro {macro.lower()}" in config:
            output["installed_macros"].append(macro)

    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_klipper_config.py <moonraker_url>")
        sys.exit(1)
    get_config(sys.argv[1])
