# Klipper Extras Database

Reference for all optional Klipper modules, macros, and third-party extensions
that the 3dprint-advisor may recommend. Each entry includes:
- What it does and why you want it
- How to detect if it's installed
- How to install it (automated)
- Config snippet to add to printer.cfg
- Moonraker update_manager snippet (for third-party repos)

---

## Category 1: Native Klipper Config Sections

These are built into Klipper — they just need a config section added to `printer.cfg`.
No external repos, no symlinks, no pip installs. Just add the config and restart.

### firmware_retraction

**What**: Moves retraction control from the slicer to Klipper firmware. Allows runtime tuning of retraction length/speed without re-slicing. Required by KAMP purge macros.
**Why you want it**: Change retraction on the fly, tune per-filament without re-slicing, required by KAMP.
**Detect**: Check if `[firmware_retraction]` exists in printer config.
**Install**: Add config section to printer.cfg, restart Klipper.

```ini
[firmware_retraction]
retract_length: 0.5          ; Direct drive default. Bowden: 2-6mm
retract_speed: 60            ; mm/s
unretract_extra_length: 0
unretract_speed: 60          ; mm/s
```

**OrcaSlicer requirement**: Enable "Use firmware retraction" in Printer Settings → General → Firmware.

### exclude_object

**What**: Allows canceling individual objects mid-print without aborting the entire job. Required by KAMP for adaptive meshing.
**Why you want it**: Cancel a failed part without wasting the rest of the plate. Required by KAMP.
**Detect**: Check if `[exclude_object]` exists in printer config.
**Install**: Add config section to printer.cfg, restart Klipper.

```ini
[exclude_object]
```

**Moonraker requirement**: Also needs this in `moonraker.conf`:
```ini
[file_manager]
enable_object_processing: True
```

**OrcaSlicer requirement**: Enable "Label objects" in Print Settings → Others.

### gcode_arcs

**What**: Enables G2/G3 arc move support. Without this, arcs are approximated as many tiny line segments, bloating gcode files and reducing surface quality on curves.
**Why you want it**: Smaller gcode files, smoother curves, reduced buffer pressure on the MCU.
**Detect**: Check if `[gcode_arcs]` exists in printer config.
**Install**: Add config section to printer.cfg, restart Klipper.

```ini
[gcode_arcs]
resolution: 0.1              ; mm — smaller = smoother arcs, more CPU
```

**OrcaSlicer requirement**: Enable "Arc fitting" in Print Settings → Others.

### skew_correction

**What**: Compensates for non-square frame geometry (XY skew). Important for dimensional accuracy.
**Why you want it**: If your frame isn't perfectly square, all prints will be slightly trapezoidal.
**Detect**: Check if `[skew_correction]` exists in printer config.
**Install**: Add config section to printer.cfg, restart Klipper.

```ini
[skew_correction]
```

**Usage**: After measuring skew (print calibration square, measure diagonals):
```
SET_SKEW XY=<AC>,<BD>,<AD>
SKEW_PROFILE SAVE=my_skew_profile
SAVE_CONFIG
```
Add to PRINT_START: `SKEW_PROFILE LOAD=my_skew_profile`
Add to PRINT_END: `SET_SKEW CLEAR=1`

### axis_twist_compensation

**What**: Compensates for gantry twist (one side of X axis higher than the other). Common on bed-slingers with single-rail X axis.
**Why you want it**: Eliminates first-layer inconsistency across the X axis caused by mechanical twist.
**Detect**: Check if `[axis_twist_compensation]` exists in printer config.
**Install**: Add config section to printer.cfg, restart Klipper.

```ini
[axis_twist_compensation]
calibrate_start_x: 10
calibrate_end_x: 225          ; Adjust to your bed width - 10
calibrate_y: 117.5            ; Middle of your Y axis
```

**Usage**: Run `AXIS_TWIST_COMPENSATION_CALIBRATE` and follow prompts.

### resonance_tester

**What**: Required for input shaper calibration. Measures resonance frequencies using an accelerometer (ADXL345, LIS2DW, MPU-6050, etc.).
**Why you want it**: Input shaper eliminates ringing/ghosting — this is how you calibrate it.
**Detect**: Check if `[resonance_tester]` exists in printer config.
**Install**: Requires accelerometer hardware connected. Add config section to printer.cfg.

```ini
[resonance_tester]
accel_chip: adxl345            ; Or lis2dw, mpu9250, etc.
probe_points:
    117.5, 117.5, 20           ; Center of your bed, 20mm above
```

**Hardware prerequisite**: ADXL345 (most common), connected via SPI to MCU or Raspberry Pi.

### input_shaper

**What**: Active vibration cancellation. Reduces ringing/ghosting on prints by applying a filter to motion commands.
**Why you want it**: Dramatically improves print quality at speed. Required for fast printing.
**Detect**: Check if `[input_shaper]` exists in printer config.
**Install**: Added automatically by `SHAPER_CALIBRATE` + `SAVE_CONFIG`. Or add manually:

```ini
[input_shaper]
shaper_freq_x: 50.0
shaper_type_x: mzv
shaper_freq_y: 40.0
shaper_type_y: mzv
```

**Note**: Values should come from `SHAPER_CALIBRATE`, not guessed.

---

## Category 2: Third-Party Klipper Modules (require git clone + install)

These are external Python modules that extend Klipper's functionality. They need to be cloned, symlinked into Klipper's extras directory, and may require additional pip packages.

### klipper_auto_speed (AUTO_SPEED)

**What**: Automated binary search for maximum acceleration and velocity by detecting missed stepper steps. Replaces manual trial-and-error speed testing.
**Why you want it**: Objectively find your printer's mechanical limits in ~10 minutes.
**Source**: https://github.com/Anonoei/klipper_auto_speed
**License**: MIT
**Detect**: Check if `[auto_speed]` exists in printer config, or if `auto_speed.py` exists in Klipper extras.

**Install commands** (run on the Klipper host via SSH):
```bash
cd ~
git clone https://github.com/Anonoei/klipper_auto_speed.git
cd klipper_auto_speed
./install.sh
```

The install script does:
1. Symlinks `auto_speed.py` → `~/klipper/klippy/extras/auto_speed.py`
2. Symlinks `autospeed/*.py` → `~/klipper/klippy/extras/autospeed/*.py`
3. Installs matplotlib in klippy-env (`~/klippy-env/bin/python -m pip install matplotlib`)
4. Restarts Klipper

**Config to add to printer.cfg**:
```ini
[auto_speed]
#axis: diag_x, diag_y    ; Axes to test. For bed-slingers, use: x, y
#margin: 20               ; mm from axis limits
#settling_home: 1         ; Home before starting
#max_missed: 1.0          ; Max missed steps (increase to 5-10 for sensorless homing)
#endstop_samples: 3       ; Endstop variance samples
#accel_min: 1000.0        ; Min accel to test
#accel_max: 50000.0       ; Max accel to test
#accel_accu: 0.05         ; Binary search accuracy (5%)
#velocity_min: 50.0       ; Min velocity to test
#velocity_max: 5000.0     ; Max velocity to test
#velocity_accu: 0.05      ; Binary search accuracy (5%)
#derate: 0.8              ; Derate results by 20% for safety margin
#validate_margin: 20.0    ; Margin for validation pattern
#validate_inner_margin: 20.0
#validate_iterations: 50  ; Validation repetitions
#results_dir: ~/printer_data/config  ; Where to save graphs
```

**Moonraker update_manager** (add to moonraker.conf):
```ini
[update_manager klipper_auto_speed]
type: git_repo
path: ~/klipper_auto_speed
origin: https://github.com/anonoei/klipper_auto_speed.git
primary_branch: main
install_script: install.sh
managed_services: klipper
```

**Bed-slinger note**: Change axis to `x, y` instead of the default `diag_x, diag_y` (diag only works on CoreXY).

**Sensorless homing note**: Increase `max_missed` to 5-10 to account for endstop variance.

### KAMP (Klipper Adaptive Meshing & Purging)

**What**: Generates bed mesh ONLY in the area where the print will be placed. Also provides adaptive purge (Voron logo purge or line purge) positioned near the print area.
**Why you want it**: Faster bed meshing (smaller area = more dense mesh), smarter purge placement.
**Source**: https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging
**License**: GPL-3.0
**Detect**: Check for KAMP macros (BED_MESH_CALIBRATE override, LINE_PURGE, VORON_PURGE, SMART_PARK) in config.

**Prerequisites**:
- `[exclude_object]` in printer.cfg
- `enable_object_processing: True` in moonraker.conf
- `[bed_mesh]` configured
- OrcaSlicer: "Label objects" enabled

**Install commands** (run on the Klipper host via SSH):
```bash
cd ~
git clone https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging.git
ln -s ~/Klipper-Adaptive-Meshing-Purging/Configuration ~/printer_data/config/KAMP
cp ~/Klipper-Adaptive-Meshing-Purging/Configuration/KAMP_Settings.cfg ~/printer_data/config/KAMP_Settings.cfg
```

**Config to add to printer.cfg**:
```ini
[include KAMP_Settings.cfg]
```

**KAMP_Settings.cfg** (already copied to config dir by install, user uncomments what they want):
- `[include ./KAMP/Adaptive_Meshing.cfg]` — adaptive bed mesh
- `[include ./KAMP/Line_Purge.cfg]` — simple line purge
- `[include ./KAMP/Voron_Purge.cfg]` — Voron logo purge (pick one purge, not both)
- `[include ./KAMP/Smart_Park.cfg]` — park near print area for final heating

**Key KAMP_Settings.cfg variables**:
```ini
[gcode_macro _KAMP_Settings]
variable_mesh_margin: 5              ; mm beyond print area for mesh
variable_fuzz_amount: 0              ; Randomize mesh bounds (for nozzle probes, max 3)
variable_probe_dock_enable: False    ; True if using dockable probe (Klicky, Euclid)
variable_attach_macro: 'Attach_Probe'
variable_detach_macro: 'Detach_Probe'
variable_purge_height: 0.8           ; Purge nozzle height
variable_tip_distance: 0             ; Filament tip to nozzle distance
variable_purge_margin: 10            ; mm between purge and print area
variable_purge_amount: 30            ; mm of filament to purge
variable_flow_rate: 12               ; Purge flow rate (12 for standard, 20 for high-flow)
variable_smart_park_height: 10       ; Park height for heating
```

**Moonraker update_manager** (add to moonraker.conf):
```ini
[update_manager Klipper-Adaptive-Meshing-Purging]
type: git_repo
channel: dev
path: ~/Klipper-Adaptive-Meshing-Purging
origin: https://github.com/kyleisah/Klipper-Adaptive-Meshing-Purging.git
managed_services: klipper
primary_branch: main
```

**OrcaSlicer PRINT_START integration**: Call `SMART_PARK` before final nozzle heating, then `LINE_PURGE` or `VORON_PURGE` after heating, right before the print starts.

---

## Category 3: Standalone Gcode Macros (just paste into printer.cfg)

These are self-contained gcode macros — no external repos, no Python modules. Just paste the macro definition into your printer.cfg (or a separate macros.cfg and `[include]` it).

### TEST_SPEED (Ellis)

**What**: Quick validation of speed/accel limits by running toolhead movement patterns and checking for missed steps via GET_POSITION.
**Why you want it**: Fast sanity check that your configured speed/accel don't cause missed steps.
**Source**: https://github.com/AndrewEllis93/Print-Tuning-Guide/blob/main/macros/TEST_SPEED.cfg
**License**: Unlicensed (community macro)
**Detect**: Check if `[gcode_macro TEST_SPEED]` exists in printer config.

**Install**: The macro source is embedded in `scripts/install_klipper_extras.sh` (see the TEST_SPEED section). The installer writes it to `~/printer_data/config/TEST_SPEED.cfg` and adds an include to printer.cfg.

**Usage**:
```
TEST_SPEED SPEED=200 ACCEL=3000 ITERATIONS=20
```
- Start conservative, increment up
- Check GET_POSITION output after each run
- If commanded vs actual positions differ by > half a full step, you exceeded the limit

**Parameters**:
| Param | Default | Description |
|-------|---------|-------------|
| SPEED | printer max_velocity | Test speed in mm/s |
| ACCEL | printer max_accel | Test acceleration in mm/s² |
| ITERATIONS | 5 | Number of pattern repetitions |
| MIN_CRUISE_RATIO | 0.5 | Minimum cruise ratio |
| BOUND | 20 | Inset from axis limits (safety margin) |

---

## Category 4: Recommended Extras by Printer Type

### All printers (universal recommendations)
- `firmware_retraction` — runtime retraction tuning
- `exclude_object` — object cancellation
- `gcode_arcs` — arc support
- KAMP — adaptive meshing + purging
- TEST_SPEED — speed validation

### Printers with accelerometer
- `resonance_tester` — if not already configured
- `input_shaper` — auto-configured by SHAPER_CALIBRATE

### Printers where speed tuning matters
- klipper_auto_speed — automated limit finding
- TEST_SPEED — manual limit validation

### Printers with dimensional accuracy needs
- `skew_correction` — frame squareness compensation
- `axis_twist_compensation` — gantry twist (bed-slingers especially)

---

## Installation Priority for Newbies

When the skill detects a fresh Klipper install with minimal config, install in this order:

1. **exclude_object** + moonraker file_manager setting (required for KAMP)
2. **firmware_retraction** (required for KAMP purge, useful for runtime tuning)
3. **gcode_arcs** (tiny config, big improvement for curves)
4. **KAMP** (adaptive meshing + purging — major quality of life)
5. **TEST_SPEED macro** (quick speed validation)
6. **skew_correction** (just enable the section, calibrate later)
7. **axis_twist_compensation** (if bed-slinger, just enable, calibrate later)
8. **klipper_auto_speed** (if user wants to push speed limits)
9. **resonance_tester** + **input_shaper** (if accelerometer present, usually already configured)
