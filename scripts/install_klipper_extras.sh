#!/usr/bin/env bash
# install_klipper_extras.sh — Automated installer for Klipper optional extras
#
# This script runs on the KLIPPER HOST (Raspberry Pi / Linux box), not on the
# local machine. The 3dprint-advisor skill executes it remotely via SSH.
#
# Usage:
#   bash install_klipper_extras.sh <moonraker_url> <extra1> [extra2] [extra3] ...
#
# Supported extras:
#   Native config sections (just add config to printer.cfg):
#     firmware_retraction, exclude_object, gcode_arcs, skew_correction,
#     axis_twist_compensation
#
#   Third-party modules (require git clone + install):
#     auto_speed, kamp
#
#   Standalone macros (paste into config):
#     test_speed
#
# Modes:
#   --check    : Only check what's missing, don't install anything (default if no extras specified)
#   --install  : Install the specified extras
#   --list     : List all available extras and their status
#
# Output: JSON to stdout with results
#
# Requirements:
#   - curl and jq available on the local machine
#   - Moonraker API accessible at the given URL
#   - SSH access to the Klipper host (for third-party module installs)

set -euo pipefail

MOONRAKER_URL="${1:-}"
MODE="--install"
EXTRAS=()

# Parse arguments
shift || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check|--install|--list)
            MODE="$1"
            ;;
        *)
            EXTRAS+=("$(echo "$1" | tr '[:upper:]' '[:lower:]')")
            ;;
    esac
    shift
done

if [[ -z "$MOONRAKER_URL" ]]; then
    echo '{"error": "Usage: install_klipper_extras.sh <moonraker_url> [--check|--install|--list] [extra1] [extra2] ..."}' 
    exit 1
fi

# Strip trailing slash
MOONRAKER_URL="${MOONRAKER_URL%/}"

# ─── Helper functions ───

api_get() {
    curl -sf --max-time 10 "${MOONRAKER_URL}${1}" 2>/dev/null || echo '{"error": "API request failed"}'
}

api_post() {
    curl -sf --max-time 30 -X POST "${MOONRAKER_URL}${1}" \
        -H "Content-Type: application/json" \
        -d "${2:-{}}" 2>/dev/null || echo '{"error": "API POST failed"}'
}

# Check if a config section exists in the printer config
config_has_section() {
    local section="$1"
    local config
    config=$(api_get "/printer/objects/query?configfile")
    if echo "$config" | python3 -c "
import sys, json
data = json.load(sys.stdin)
config = data.get('result', {}).get('status', {}).get('configfile', {}).get('config', {})
sys.exit(0 if '$section' in config else 1)
" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Check if a gcode macro exists
macro_exists() {
    local macro_name="$1"
    local macros
    macros=$(api_get "/printer/objects/list")
    if echo "$macros" | python3 -c "
import sys, json
data = json.load(sys.stdin)
objects = data.get('result', {}).get('objects', [])
target = 'gcode_macro ${macro_name}'
sys.exit(0 if target in objects else 1)
" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Get the Klipper host's SSH info from Moonraker
get_klipper_host() {
    # Moonraker runs on the same host as Klipper, so the host is the URL's hostname
    echo "$MOONRAKER_URL" | sed -E 's|https?://||; s|:[0-9]+.*||; s|/.*||'
}

# Add a config section via Moonraker's file API
# This appends to printer.cfg
append_to_printer_cfg() {
    local content="$1"
    local host
    host=$(get_klipper_host)
    
    # Use Moonraker's file API to read current printer.cfg
    local current_cfg
    current_cfg=$(curl -sf "${MOONRAKER_URL}/server/files/config/printer.cfg" 2>/dev/null) || {
        echo "ERROR: Could not read printer.cfg via Moonraker API"
        return 1
    }
    
    # Check if content already exists (avoid duplicates)
    local section_name
    section_name=$(echo "$content" | head -1 | tr -d '[]' | tr -d ' ')
    if echo "$current_cfg" | grep -q "\\[$section_name\\]"; then
        echo "SKIP: [$section_name] already exists in printer.cfg"
        return 0
    fi
    
    # Append the new config
    local new_cfg="${current_cfg}

# --- Added by 3dprint-advisor ---
${content}
"
    
    # Upload the modified printer.cfg back via Moonraker
    local tmpfile
    tmpfile=$(mktemp /tmp/printer_cfg_XXXXXX.cfg)
    echo "$new_cfg" > "$tmpfile"
    
    curl -sf -X POST "${MOONRAKER_URL}/server/files/upload" \
        -F "file=@${tmpfile};filename=printer.cfg" \
        -F "root=config" >/dev/null 2>&1 || {
        rm -f "$tmpfile"
        echo "ERROR: Could not upload printer.cfg via Moonraker API"
        return 1
    }
    
    rm -f "$tmpfile"
    echo "OK: Added [$section_name] to printer.cfg"
}

# Append to moonraker.conf via Moonraker's file API
append_to_moonraker_conf() {
    local content="$1"
    
    local current_conf
    current_conf=$(curl -sf "${MOONRAKER_URL}/server/files/config/moonraker.conf" 2>/dev/null) || {
        echo "ERROR: Could not read moonraker.conf via Moonraker API"
        return 1
    }
    
    # Check for duplicates
    local section_name
    section_name=$(echo "$content" | head -1 | sed 's/\[//;s/\].*//')
    if echo "$current_conf" | grep -q "$section_name"; then
        echo "SKIP: [$section_name] already exists in moonraker.conf"
        return 0
    fi
    
    local new_conf="${current_conf}

# --- Added by 3dprint-advisor ---
${content}
"
    
    local tmpfile
    tmpfile=$(mktemp /tmp/moonraker_conf_XXXXXX.conf)
    echo "$new_conf" > "$tmpfile"
    
    curl -sf -X POST "${MOONRAKER_URL}/server/files/upload" \
        -F "file=@${tmpfile};filename=moonraker.conf" \
        -F "root=config" >/dev/null 2>&1 || {
        rm -f "$tmpfile"
        echo "ERROR: Could not upload moonraker.conf via Moonraker API"
        return 1
    }
    
    rm -f "$tmpfile"
    echo "OK: Added [$section_name] to moonraker.conf"
}

# Execute a command on the Klipper host via Moonraker's shell_command (if available)
# or via SSH as fallback
run_on_host() {
    local cmd="$1"
    local host
    host=$(get_klipper_host)
    
    # Try SSH first (most reliable for install commands)
    # The user may need to set up SSH keys beforehand
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "pi@${host}" "$cmd" 2>/dev/null || \
    ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "${host}" "$cmd" 2>/dev/null || {
        echo "ERROR: Could not SSH to Klipper host at ${host}. Try: ssh pi@${host}"
        return 1
    }
}

# Write a file to the config directory via Moonraker's file upload API
write_config_file() {
    local filename="$1"
    local content="$2"
    
    local tmpfile
    tmpfile=$(mktemp "/tmp/${filename}_XXXXXX")
    echo "$content" > "$tmpfile"
    
    curl -sf -X POST "${MOONRAKER_URL}/server/files/upload" \
        -F "file=@${tmpfile};filename=${filename}" \
        -F "root=config" >/dev/null 2>&1 || {
        rm -f "$tmpfile"
        echo "ERROR: Could not upload ${filename} via Moonraker API"
        return 1
    }
    
    rm -f "$tmpfile"
    echo "OK: Wrote ${filename} to config directory"
}

# Restart Klipper firmware via Moonraker
restart_klipper() {
    api_post "/printer/firmware_restart" "{}" >/dev/null 2>&1
    echo "OK: Klipper firmware restart requested"
}

# Restart Moonraker service
restart_moonraker() {
    api_post "/machine/services/restart?service=moonraker" "{}" >/dev/null 2>&1
    echo "OK: Moonraker restart requested"
}

# ─── Check status of all extras ───

check_all() {
    local results=()
    
    # Native config sections
    for section in firmware_retraction exclude_object gcode_arcs skew_correction axis_twist_compensation input_shaper resonance_tester; do
        if config_has_section "$section"; then
            results+=("\"$section\": \"installed\"")
        else
            results+=("\"$section\": \"missing\"")
        fi
    done
    
    # Auto Speed
    if config_has_section "auto_speed"; then
        results+=("\"auto_speed\": \"installed\"")
    else
        results+=("\"auto_speed\": \"missing\"")
    fi
    
    # KAMP (check for the KAMP settings macro)
    if macro_exists "_KAMP_Settings"; then
        results+=("\"kamp\": \"installed\"")
    else
        results+=("\"kamp\": \"missing\"")
    fi
    
    # TEST_SPEED macro
    if macro_exists "TEST_SPEED"; then
        results+=("\"test_speed\": \"installed\"")
    else
        results+=("\"test_speed\": \"missing\"")
    fi
    
    # Check moonraker file_manager
    local moonraker_conf
    moonraker_conf=$(curl -sf "${MOONRAKER_URL}/server/files/config/moonraker.conf" 2>/dev/null || echo "")
    if echo "$moonraker_conf" | grep -q "enable_object_processing.*True"; then
        results+=("\"moonraker_object_processing\": \"enabled\"")
    else
        results+=("\"moonraker_object_processing\": \"disabled\"")
    fi
    
    echo "{$(IFS=,; echo "${results[*]}")}"
}

# ─── Install individual extras ───

install_firmware_retraction() {
    echo "Installing firmware_retraction..."
    append_to_printer_cfg "[firmware_retraction]
retract_length: 0.5
retract_speed: 60
unretract_extra_length: 0
unretract_speed: 60"
}

install_exclude_object() {
    echo "Installing exclude_object..."
    append_to_printer_cfg "[exclude_object]"
    
    # Also enable object processing in moonraker
    append_to_moonraker_conf "[file_manager]
enable_object_processing: True"
}

install_gcode_arcs() {
    echo "Installing gcode_arcs..."
    append_to_printer_cfg "[gcode_arcs]
resolution: 0.1"
}

install_skew_correction() {
    echo "Installing skew_correction..."
    append_to_printer_cfg "[skew_correction]"
}

install_axis_twist_compensation() {
    echo "Installing axis_twist_compensation..."
    # Get bed size from config to set reasonable defaults
    local bed_x_max bed_y_max
    bed_x_max=$(api_get "/printer/objects/query?configfile" | python3 -c "
import sys, json
data = json.load(sys.stdin)
config = data.get('result',{}).get('status',{}).get('configfile',{}).get('config',{})
stepper = config.get('stepper_x', {})
print(stepper.get('position_max', '235'))
" 2>/dev/null || echo "235")
    bed_y_max=$(api_get "/printer/objects/query?configfile" | python3 -c "
import sys, json
data = json.load(sys.stdin)
config = data.get('result',{}).get('status',{}).get('configfile',{}).get('config',{})
stepper = config.get('stepper_y', {})
print(stepper.get('position_max', '235'))
" 2>/dev/null || echo "235")
    
    local y_center
    y_center=$(python3 -c "print(int($bed_y_max) // 2)")
    local x_end
    x_end=$(python3 -c "print(int($bed_x_max) - 10)")
    
    append_to_printer_cfg "[axis_twist_compensation]
calibrate_start_x: 10
calibrate_end_x: ${x_end}
calibrate_y: ${y_center}"
}

install_auto_speed() {
    echo "Installing klipper_auto_speed..."
    
    # This requires running commands on the Klipper host
    local result
    result=$(run_on_host "
        set -e
        cd ~
        if [ -d klipper_auto_speed ]; then
            echo 'Repo already cloned, updating...'
            cd klipper_auto_speed && git pull
        else
            git clone https://github.com/Anonoei/klipper_auto_speed.git
            cd klipper_auto_speed
        fi
        ./install.sh
    " 2>&1) || {
        echo "ERROR: Failed to install auto_speed on Klipper host. SSH access required."
        echo "Manual install: ssh to your printer, then run:"
        echo "  cd ~ && git clone https://github.com/Anonoei/klipper_auto_speed.git && cd klipper_auto_speed && ./install.sh"
        return 1
    }
    echo "$result"
    
    # Add config section
    append_to_printer_cfg "[auto_speed]
#axis: diag_x, diag_y
#margin: 20
#settling_home: 1
#max_missed: 1.0
#endstop_samples: 3
#accel_min: 1000.0
#accel_max: 50000.0
#accel_accu: 0.05
#velocity_min: 50.0
#velocity_max: 5000.0
#velocity_accu: 0.05
#derate: 0.8"
    
    # Add moonraker update manager
    append_to_moonraker_conf "[update_manager klipper_auto_speed]
type: git_repo
path: ~/klipper_auto_speed
origin: https://github.com/anonoei/klipper_auto_speed.git
primary_branch: main
install_script: install.sh
managed_services: klipper"
}

install_kamp() {
    echo "Installing KAMP..."
    
    # Ensure prerequisites
    if ! config_has_section "exclude_object"; then
        echo "Installing prerequisite: exclude_object..."
        install_exclude_object
    fi
    if ! config_has_section "firmware_retraction"; then
        echo "Installing prerequisite: firmware_retraction..."
        install_firmware_retraction
    fi
    
    # Clone KAMP on the Klipper host
    local result
    result=$(run_on_host "
        set -e
        cd ~
        if [ -d Klipper-Adaptive-Meshing-Purging ]; then
            echo 'Repo already cloned, updating...'
            cd Klipper-Adaptive-Meshing-Purging && git pull
        else
            git clone https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging.git
        fi
        # Create symlink if not exists
        if [ ! -L ~/printer_data/config/KAMP ]; then
            ln -s ~/Klipper-Adaptive-Meshing-Purging/Configuration ~/printer_data/config/KAMP
        fi
        # Copy settings if not exists
        if [ ! -f ~/printer_data/config/KAMP_Settings.cfg ]; then
            cp ~/Klipper-Adaptive-Meshing-Purging/Configuration/KAMP_Settings.cfg ~/printer_data/config/KAMP_Settings.cfg
        fi
    " 2>&1) || {
        echo "ERROR: Failed to install KAMP on Klipper host. SSH access required."
        echo "Manual install: ssh to your printer, then run:"
        echo "  cd ~ && git clone https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging.git"
        echo "  ln -s ~/Klipper-Adaptive-Meshing-Purging/Configuration ~/printer_data/config/KAMP"
        echo "  cp ~/Klipper-Adaptive-Meshing-Purging/Configuration/KAMP_Settings.cfg ~/printer_data/config/KAMP_Settings.cfg"
        return 1
    }
    echo "$result"
    
    # Uncomment the includes in KAMP_Settings.cfg — enable adaptive meshing + line purge + smart park
    # We do this by writing a configured KAMP_Settings.cfg
    write_config_file "KAMP_Settings.cfg" "# KAMP Settings — configured by 3dprint-advisor
# See: https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging

[include ./KAMP/Adaptive_Meshing.cfg]
[include ./KAMP/Line_Purge.cfg]
# [include ./KAMP/Voron_Purge.cfg]   # Alternative purge style — uncomment to use instead of Line_Purge
[include ./KAMP/Smart_Park.cfg]

[gcode_macro _KAMP_Settings]
variable_mesh_margin: 5
variable_fuzz_amount: 0
variable_probe_dock_enable: False
variable_attach_macro: 'Attach_Probe'
variable_detach_macro: 'Detach_Probe'
variable_purge_height: 0.8
variable_tip_distance: 0
variable_purge_margin: 10
variable_purge_amount: 30
variable_flow_rate: 12
variable_smart_park_height: 10"
    
    # Add include to printer.cfg
    append_to_printer_cfg "# KAMP - Klipper Adaptive Meshing & Purging
# Uncomment the next line if not already included:
# [include KAMP_Settings.cfg]"
    
    # Note: We can't easily uncomment a line in an existing printer.cfg section,
    # so we add a comment telling the user. The append_to_printer_cfg function
    # already handles deduplication.
    
    # Add moonraker update manager
    append_to_moonraker_conf "[update_manager Klipper-Adaptive-Meshing-Purging]
type: git_repo
channel: dev
path: ~/Klipper-Adaptive-Meshing-Purging
origin: https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging.git
managed_services: klipper
primary_branch: main"
}

install_test_speed() {
    echo "Installing TEST_SPEED macro..."
    
    # Write the TEST_SPEED macro to a config file
    # Source: https://github.com/AndrewEllis93/Print-Tuning-Guide/blob/main/macros/TEST_SPEED.cfg
    write_config_file "TEST_SPEED.cfg" '# TEST_SPEED macro — from Ellis Print Tuning Guide
# Source: https://github.com/AndrewEllis93/Print-Tuning-Guide
# Usage: TEST_SPEED SPEED=200 ACCEL=3000 ITERATIONS=20

[gcode_macro TEST_SPEED]
description: Test for max speed and acceleration parameters for the printer. Procedure: Home -> ReadPositionFromMCU -> MovesToolhead@Vel&Accel -> Home -> ReadPositionfromMCU
gcode:
    # Speed
    {% set speed  = params.SPEED|default(printer.configfile.settings.printer.max_velocity)|int %}
    # Iterations
    {% set iterations = params.ITERATIONS|default(5)|int %}
    # Acceleration
    {% set accel  = params.ACCEL|default(printer.configfile.settings.printer.max_accel)|int %}
    # Minimum Cruise Ratio
    {% set min_cruise_ratio = params.MIN_CRUISE_RATIO|default(0.5)|float %}
    # Bounding inset for large pattern
    {% set bound = params.BOUND|default(20)|int %}
    # Size for small pattern box
    {% set smallpatternsize = SMALLPATTERNSIZE|default(20)|int %}
    
    # Large pattern
        {% set x_min = printer.toolhead.axis_minimum.x %}
        {% if x_min < 0 %}
            {% set x_min = 0 %}
        {% endif %}
        {% set y_min = printer.toolhead.axis_minimum.y %}
        {% if y_min < 0 %}
            {% set y_min = 0 %}
        {% endif %}
        {% set x_min = x_min + bound %}
        {% set x_max = printer.toolhead.axis_maximum.x - bound %}
        {% set y_min = y_min + bound %}
        {% set y_max = printer.toolhead.axis_maximum.y - bound %}

    # Small pattern at center
        {% set x_center = (printer.toolhead.axis_minimum.x|float + printer.toolhead.axis_maximum.x|float ) / 2 %}
        {% set y_center = (printer.toolhead.axis_minimum.y|float + printer.toolhead.axis_maximum.y|float ) / 2 %}
        {% set x_center_min = x_center - (smallpatternsize/2) %}
        {% set x_center_max = x_center + (smallpatternsize/2) %}
        {% set y_center_min = y_center - (smallpatternsize/2) %}
        {% set y_center_max = y_center + (smallpatternsize/2) %}

    # Save current gcode state
    SAVE_GCODE_STATE NAME=TEST_SPEED
    
    { action_respond_info("TEST_SPEED: starting %d iterations at speed %d, accel %d" % (iterations, speed, accel)) }
    
    # Home and get position for comparison later:
        M400
        G28
        {% if printer.configfile.settings.quad_gantry_level %}
            {% if printer.quad_gantry_level.applied == False %}
                QUAD_GANTRY_LEVEL
                G28 Z
            {% endif %}
        {% endif %} 
        G90
        G1 X{printer.toolhead.axis_maximum.x-50} Y{printer.toolhead.axis_maximum.y-50} F{30*60}
        M400
        G28 X Y
        G0 X{printer.toolhead.axis_maximum.x-1} Y{printer.toolhead.axis_maximum.y-1} F{30*60}
        G4 P1000 
        GET_POSITION

    # Go to starting position
    G0 X{x_min} Y{y_min} Z{bound + 10} F{speed*60}

    # Set new limits
    {% if printer.configfile.settings.printer.minimum_cruise_ratio is defined %}
        SET_VELOCITY_LIMIT VELOCITY={speed} ACCEL={accel} MINIMUM_CRUISE_RATIO={min_cruise_ratio}
    {% else %}
        SET_VELOCITY_LIMIT VELOCITY={speed} ACCEL={accel} ACCEL_TO_DECEL={accel / 2}
    {% endif %}

    {% for i in range(iterations) %}
        # Large pattern diagonals
        G0 X{x_min} Y{y_min} F{speed*60}
        G0 X{x_max} Y{y_max} F{speed*60}
        G0 X{x_min} Y{y_min} F{speed*60}
        G0 X{x_max} Y{y_min} F{speed*60}
        G0 X{x_min} Y{y_max} F{speed*60}
        G0 X{x_max} Y{y_min} F{speed*60}
        
        # Large pattern box
        G0 X{x_min} Y{y_min} F{speed*60}
        G0 X{x_min} Y{y_max} F{speed*60}
        G0 X{x_max} Y{y_max} F{speed*60}
        G0 X{x_max} Y{y_min} F{speed*60}
    
        # Small pattern diagonals
        G0 X{x_center_min} Y{y_center_min} F{speed*60}
        G0 X{x_center_max} Y{y_center_max} F{speed*60}
        G0 X{x_center_min} Y{y_center_min} F{speed*60}
        G0 X{x_center_max} Y{y_center_min} F{speed*60}
        G0 X{x_center_min} Y{y_center_max} F{speed*60}
        G0 X{x_center_max} Y{y_center_min} F{speed*60}
        
        # Small pattern box
        G0 X{x_center_min} Y{y_center_min} F{speed*60}
        G0 X{x_center_min} Y{y_center_max} F{speed*60}
        G0 X{x_center_max} Y{y_center_max} F{speed*60}
        G0 X{x_center_max} Y{y_center_min} F{speed*60}
    {% endfor %}

    # Restore max speed/accel to configured values
    {% if printer.configfile.settings.printer.minimum_cruise_ratio is defined %}
        SET_VELOCITY_LIMIT VELOCITY={printer.configfile.settings.printer.max_velocity} ACCEL={printer.configfile.settings.printer.max_accel} MINIMUM_CRUISE_RATIO={printer.configfile.settings.printer.minimum_cruise_ratio} 
    {% else %}
        SET_VELOCITY_LIMIT VELOCITY={printer.configfile.settings.printer.max_velocity} ACCEL={printer.configfile.settings.printer.max_accel} ACCEL_TO_DECEL={printer.configfile.settings.printer.max_accel_to_decel}
    {% endif %}

    # Re-home and get position again for comparison:
        M400
        G28
        G90
        G0 X{printer.toolhead.axis_maximum.x-1} Y{printer.toolhead.axis_maximum.y-1} F{30*60}
        G4 P1000 
        GET_POSITION

    # Restore previous gcode state
    RESTORE_GCODE_STATE NAME=TEST_SPEED'
    
    # Add include to printer.cfg
    append_to_printer_cfg "# TEST_SPEED macro — Ellis Print Tuning Guide
[include TEST_SPEED.cfg]"
}

# ─── Main logic ───

# Verify Moonraker is reachable
if ! curl -sf --max-time 5 "${MOONRAKER_URL}/printer/info" >/dev/null 2>&1; then
    echo '{"error": "Cannot reach Moonraker at '"${MOONRAKER_URL}"'. Is the printer on and connected?"}'
    exit 1
fi

case "$MODE" in
    --check|--list)
        check_all
        ;;
    --install)
        if [[ ${#EXTRAS[@]} -eq 0 ]]; then
            echo '{"error": "No extras specified. Use: install_klipper_extras.sh <url> extra1 extra2 ..."}'
            exit 1
        fi
        
        RESULTS=()
        NEEDS_KLIPPER_RESTART=false
        NEEDS_MOONRAKER_RESTART=false
        
        for extra in "${EXTRAS[@]}"; do
            echo "--- Processing: $extra ---"
            case "$extra" in
                firmware_retraction)
                    if config_has_section "firmware_retraction"; then
                        RESULTS+=("\"firmware_retraction\": \"already_installed\"")
                    else
                        install_firmware_retraction
                        RESULTS+=("\"firmware_retraction\": \"installed\"")
                        NEEDS_KLIPPER_RESTART=true
                    fi
                    ;;
                exclude_object)
                    if config_has_section "exclude_object"; then
                        RESULTS+=("\"exclude_object\": \"already_installed\"")
                    else
                        install_exclude_object
                        RESULTS+=("\"exclude_object\": \"installed\"")
                        NEEDS_KLIPPER_RESTART=true
                        NEEDS_MOONRAKER_RESTART=true
                    fi
                    ;;
                gcode_arcs)
                    if config_has_section "gcode_arcs"; then
                        RESULTS+=("\"gcode_arcs\": \"already_installed\"")
                    else
                        install_gcode_arcs
                        RESULTS+=("\"gcode_arcs\": \"installed\"")
                        NEEDS_KLIPPER_RESTART=true
                    fi
                    ;;
                skew_correction)
                    if config_has_section "skew_correction"; then
                        RESULTS+=("\"skew_correction\": \"already_installed\"")
                    else
                        install_skew_correction
                        RESULTS+=("\"skew_correction\": \"installed\"")
                        NEEDS_KLIPPER_RESTART=true
                    fi
                    ;;
                axis_twist_compensation)
                    if config_has_section "axis_twist_compensation"; then
                        RESULTS+=("\"axis_twist_compensation\": \"already_installed\"")
                    else
                        install_axis_twist_compensation
                        RESULTS+=("\"axis_twist_compensation\": \"installed\"")
                        NEEDS_KLIPPER_RESTART=true
                    fi
                    ;;
                auto_speed)
                    if config_has_section "auto_speed"; then
                        RESULTS+=("\"auto_speed\": \"already_installed\"")
                    else
                        install_auto_speed
                        RESULTS+=("\"auto_speed\": \"installed\"")
                        NEEDS_KLIPPER_RESTART=true
                        NEEDS_MOONRAKER_RESTART=true
                    fi
                    ;;
                kamp)
                    if macro_exists "_KAMP_Settings"; then
                        RESULTS+=("\"kamp\": \"already_installed\"")
                    else
                        install_kamp
                        RESULTS+=("\"kamp\": \"installed\"")
                        NEEDS_KLIPPER_RESTART=true
                        NEEDS_MOONRAKER_RESTART=true
                    fi
                    ;;
                test_speed)
                    if macro_exists "TEST_SPEED"; then
                        RESULTS+=("\"test_speed\": \"already_installed\"")
                    else
                        install_test_speed
                        RESULTS+=("\"test_speed\": \"installed\"")
                        NEEDS_KLIPPER_RESTART=true
                    fi
                    ;;
                *)
                    RESULTS+=("\"$extra\": \"unknown_extra\"")
                    ;;
            esac
        done
        
        # Restart services if needed
        if [[ "$NEEDS_MOONRAKER_RESTART" == true ]]; then
            restart_moonraker
            sleep 3  # Give moonraker time to restart before we restart klipper
        fi
        if [[ "$NEEDS_KLIPPER_RESTART" == true ]]; then
            restart_klipper
        fi
        
        echo ""
        echo "{$(IFS=,; echo "${RESULTS[*]}"), \"klipper_restarted\": $NEEDS_KLIPPER_RESTART, \"moonraker_restarted\": $NEEDS_MOONRAKER_RESTART}"
        ;;
esac
