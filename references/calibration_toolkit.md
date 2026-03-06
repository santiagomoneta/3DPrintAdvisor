# Calibration Toolkit — Complete Workflow

## Calibration Order

Always calibrate in this order. Each step depends on the previous ones being correct.

```
0. Belt Tension  →  1. Mechanical     →  2. Per-Printer     →  3. Per-Filament     →  4. Per-Process     →  5. Validate
   (physical)        (frame/motion)       (one-time tuning)     (per material)         (per layer height)     (test prints)
```

Belt tension is step zero because it has no software component — it's a physical prerequisite that affects every subsequent calibration. Get belts right first, then everything else builds on a solid foundation.

### Detailed per-filament ordering (Phase 2)

Within per-filament calibration, order matters. This sequence is derived from the Sgail7 Ultimate Filament Tuning Guide:

```
Temperature → Max Volumetric Flow → Pressure Advance → Flow Rate → Retraction
  → Fan Speed → Min Layer Time → Min Layer Speed → Bridge Flow → Validate
```

**Critical dependency**: If flow rate is >10% off from the default, PA must be re-calibrated after flow correction. This is why some guides recommend flow before PA — but testing PA first gives a better starting point for the flow test print itself. If you find flow ratio needs large correction (>1.10 or <0.90), redo PA afterward.

---

## Phase 1: Mechanical Calibration

### 1.0 Belt Tension (manual — no Klipper setting)

**What**: Correct belt tension is the foundation of everything else. Too loose → backlash, ringing, skipped steps, shifted layers. Too tight → premature bearing/stepper wear, increased motor load, reduced max speed.
**When**: Before ANY other calibration. Re-check periodically (belts stretch over time), after any frame/rail work, or if input shaper results change unexpectedly.
**Klipper config**: None — this is purely physical adjustment.

**Method 1: Frequency measurement (most accurate)**

Use a smartphone microphone app to measure the belt's resonant frequency when plucked like a guitar string:

1. Power off the printer (steppers disengaged) or use `M84` to release motors
2. Pluck the longest free span of each belt (X and Y) — treat it like a guitar string
3. Use one of these apps to measure the fundamental frequency:
   - **Gates Carbon Drive** (iOS/Android) — designed for belt frequency measurement
   - **Spectroid** (Android) — FFT spectrum analyzer, shows peak frequency
   - **Spectral Pro** (iOS) — spectrum analyzer
   - Any guitar tuner app that shows Hz (not just note names)
4. Target frequencies depend on belt type and length:

| Belt | Printer Type | Target Frequency | Notes |
|------|-------------|-----------------|-------|
| GT2 6mm (standard) | Ender 3 / bed-slinger | 80-120 Hz | Lower end for Y (longer belt) |
| GT2 6mm | Voron / CoreXY | 100-150 Hz | Both belts should match within 5 Hz |
| GT2 9mm | Voron / CoreXY | 100-140 Hz | Wider belt, slightly different target |

- **X and Y belts should be within 5-10 Hz of each other** for consistent print quality
- The exact frequency matters less than both belts matching
- Higher frequency = tighter belt
- If you can't get a clean reading, try plucking more gently or closer to the middle of the span

**Method 2: Manual feel (quick check)**
1. Press the belt at the midpoint of its longest span
2. It should deflect ~2-3mm with moderate finger pressure
3. It should "twang" when plucked, not thud
4. No visible slack when the axis moves

**Method 3: Print-based validation**
1. Print a ringing test (cube with sharp corners)
2. Ringing on X features → check X belt
3. Ringing on Y features → check Y belt
4. Asymmetric ringing → belts not equally tensioned

**Relationship to other calibrations**:
- Belt tension directly affects input shaper results — ALWAYS tension belts BEFORE running `SHAPER_CALIBRATE`
- A loose belt shifts the resonance frequency and may cause input shaper to pick a suboptimal shaper type
- If your input shaper recommends `3hump_ei` or `2hump_ei`, suspect a mechanical issue (loose belt, loose screw, worn bearing) before accepting it
- After re-tensioning belts, you MUST re-run input shaper calibration

### 1.1 Input Shaper (requires accelerometer)

**What**: Measures resonance frequencies, picks optimal shaper to cancel ringing/ghosting.
**When**: After any mechanical change (new belt, new rail, tightened screws).
**Tool**: ADXL345 accelerometer + Klipper `SHAPER_CALIBRATE`

```
# Full auto-calibration (recommended)
SHAPER_CALIBRATE

# Or per-axis
SHAPER_CALIBRATE AXIS=X
SHAPER_CALIBRATE AXIS=Y
```

**Interpreting results**:
- Klipper picks the shaper that gives best quality at highest acceleration
- Common shapers by quality: `mzv` > `ei` > `2hump_ei` > `3hump_ei`
- `3hump_ei` suggests complex/multiple resonances — check for loose parts
- For bed-slingers: `ei` on Y is common and expected (heavy bed)
- The `max_accel` from shaper test = max accel before smoothing degrades quality
- Save results: `SAVE_CONFIG`

### 1.2 AUTO_SPEED (klipper_auto_speed module)

**What**: Binary search for max acceleration/velocity by detecting missed steps.
**When**: After input shaper, after any motor/driver/belt change.
**Tool**: `AUTO_SPEED` command (requires klipper_auto_speed installed)

> **Not installed?** AUTO_SPEED is a third-party Klipper module, not built in. If it's missing, the 3dprint-advisor can install it automatically — run `scripts/install_klipper_extras.sh <moonraker_url> auto_speed`. Or install manually: `cd ~ && git clone https://github.com/Anonoei/klipper_auto_speed.git && cd klipper_auto_speed && ./install.sh`. See `references/klipper_extras_database.md` for full details.
>
> **Alternatives if you skip AUTO_SPEED**: Use TEST_SPEED (section 1.3) for manual speed validation, or simply start with conservative values from `[printer]` max_velocity and max_accel and increment gradually with test prints.

```
# Full test (accel + velocity + validate)
AUTO_SPEED

# Just acceleration on specific axis
AUTO_SPEED_ACCEL AXIS="y"

# Just velocity
AUTO_SPEED_VELOCITY

# Validate current settings (Ellis pattern)
AUTO_SPEED_VALIDATE

# Graph velocity-accel relationship
AUTO_SPEED_GRAPH VELOCITY_MIN=100 VELOCITY_MAX=500 VELOCITY_DIV=9
```

**Key parameters**:
- `MAX_MISSED=1.0` — default, too low for sensorless homing (use 5-10)
- `DERATE=0.8` — recommended results are 80% of measured max
- `ACCEL_MAX=10000` — ceiling for binary search
- Takes ~10 minutes

### 1.3 TEST_SPEED Macro (Ellis)

**What**: Quick validation of speed/accel by running patterns and checking for lost steps.
**When**: Quick check after changing speed settings.
**Tool**: `TEST_SPEED` macro

> **Not installed?** TEST_SPEED is a community macro, not built into Klipper. If it's missing, the 3dprint-advisor can install it automatically — run `scripts/install_klipper_extras.sh <moonraker_url> test_speed`. This writes the macro to `TEST_SPEED.cfg` in your config directory and adds an `[include]` to printer.cfg. See `references/klipper_extras_database.md` for the full macro source.
>
> **Alternatives if you skip TEST_SPEED**: Print a speed test cube at increasing speeds. If you see layer shifts or hear grinding, you've exceeded your limit. Less precise than TEST_SPEED but requires no macro installation.

```
# Test at specific speed and accel
TEST_SPEED SPEED=200 ACCEL=3000 ITERATIONS=20

# Start conservative, increment up
TEST_SPEED SPEED=150 ACCEL=2000 ITERATIONS=20
TEST_SPEED SPEED=200 ACCEL=2500 ITERATIONS=20
TEST_SPEED SPEED=250 ACCEL=3000 ITERATIONS=20
```

**Pass/fail**: Check `GET_POSITION` output — if commanded vs actual differ by >half a step, you exceeded the limit.

### 1.4 Skew Correction

**What**: Compensates for non-square XY frame geometry.
**When**: Once after build, or if you notice dimensional inaccuracy on XY.
**Tool**: Print a calibration square, measure diagonals, compute skew.

```
# After measuring skew
SET_SKEW XY=<AC>,<BD>,<AD>
SKEW_PROFILE SAVE=my_skew_profile
SAVE_CONFIG
```

Add to PRINT_START: `SKEW_PROFILE LOAD=my_skew_profile`
Add to PRINT_END: `SET_SKEW CLEAR=1`

### 1.5 Elephant's Foot Compensation

**What**: First layer spreads wider than intended due to nozzle squish. Compensates by shrinking the first layer XY dimensions slightly.
**When**: Once per printer, after bed leveling/Z-offset is dialed in. May need revisiting if you change bed surface or first layer settings significantly.
**Scope**: Per-printer (one-time). The setting is in the process profile but the value is a function of your Z-offset and bed surface.
**Tool**: Print a calibration cube or first-layer test, measure the bottom edge with calipers.

**Procedure**:
1. Print a 20mm calibration cube with your standard first layer settings
2. Measure the width of the bottom 1-2 layers vs the upper layers
3. The difference is your elephant's foot — typically 0.1-0.2mm
4. Set `elefant_foot_compensation` in OrcaSlicer process profile (note OrcaSlicer's spelling)
5. Typical values: 0.1mm for PEI, 0.15mm for glass, 0.05mm for textured PEI

**Why it's per-printer**: The elephant's foot is caused by the mechanical squish of your Z-offset + bed surface adhesion. Different filaments have slightly different flow characteristics on the first layer, but the dominant factor is your hardware setup. One value works across most filaments.

### 1.6 Infill/Perimeter Overlap (Encroachment)

**What**: Controls how much the infill overlaps with inner wall perimeters. Too little → pinholes and weak wall-infill bond. Too much → over-extrusion at corners where infill meets walls.
**When**: Once per printer, after flow rate calibration is done for at least one filament.
**Scope**: Per-printer (one-time). The optimal overlap % depends on your nozzle geometry and extruder precision, not the filament.
**Tool**: OrcaSlicer's infill/wall overlap percentage setting.

**Procedure**:
1. Print a simple box (40x40x20mm) with 2 walls, 20% infill, at your normal speed
2. Slice the top off (or print only 5mm tall) and inspect the cross-section
3. Look for pinholes where infill meets the inner wall — increase overlap
4. Look for bulging at corners where infill meets walls — decrease overlap
5. Default is 25% in OrcaSlicer; most printers need 15-30%
6. Adjust in 5% increments

---

## Calibration Scope: What Needs Redoing When?

Before diving into procedures, understand what each calibration depends on.
This determines whether you do it once or repeat it across process profiles.

### Per-Filament (do once per material/brand/color, valid for ALL process profiles)

| Calibration | Why It's Per-Filament | Saved To |
|-------------|----------------------|----------|
| **Temperature tower** | Material property — chemical composition determines optimal temp | Filament profile |
| **Flow rate** | Filament diameter tolerance + material compressibility | Filament profile |
| **Retraction** | Material viscosity + extruder type (direct/bowden) | Filament profile |
| **Max volumetric flow** | Hotend melt capacity × filament viscosity | Filament profile |
| **Fan speed (min/max/bridge)** | Material thermal sensitivity — how much cooling before layer adhesion degrades | Filament profile |
| **Minimum layer time** | Material cooling rate — how fast can small layers cool before curling | Filament profile |
| **Minimum layer speed** | Sweet spot where cooling works but nozzle doesn't reheat deposited filament | Filament profile |
| **Shrinkage compensation** | Material expansion/contraction rate (mainly ABS/ASA/Nylon) | Filament profile |

These are stable across process profiles. A PLA spool wants the same temperature and flow ratio whether you print at 0.08mm miniature or 0.24mm prototype layer height.

### Per-Process (varies by layer height — the exception)

| Calibration | Why It's Per-Process | Saved To |
|-------------|---------------------|----------|
| **Bridge flow rate** | Bridge cooling and sag behavior changes with layer height — thicker layers need different flow ratio | Process profile |

Bridge flow rate is the ONE calibration that genuinely varies by layer height. A 0.08mm layer needs a different bridge flow ratio than a 0.24mm layer. You will need to test this for every layer height profile you use. This is a small test (~10 min) but it IS per-process.

### Per-Filament BUT Speed-Dependent: Pressure Advance

PA is the exception. Research confirms PA varies significantly with speed, acceleration, and layer height because all three change the volumetric flow rate through the nozzle:

- PA tested at 50mm/s, 1000 accel → **0.036**
- PA tested at 200mm/s, 4000 accel → **0.024**
- That's a **33% variation** for the same filament on the same printer

This means a single PA value is always a compromise. If you calibrate PA on a "functional" profile at 80mm/s and then print a "prototype" at 150mm/s, PA will be slightly wrong.

**OrcaSlicer's solution: Adaptive Pressure Advance**

OrcaSlicer has a built-in Adaptive PA calibration that solves this:
1. Runs 12-20 PA tests across a matrix of speeds × accelerations
2. Builds a mathematical model: PA = f(flow_rate, acceleration)
3. Dynamically adjusts PA per-line in the generated G-code
4. Result stored in the filament profile → works across ALL process profiles

**Recommendation**:
- If user prints at multiple speeds/layer heights → **strongly recommend Adaptive PA**
- If user only uses one process profile → static PA is fine
- If user doesn't want to run 12+ test prints → single static PA is an acceptable compromise

### Per-Printer (hardware, independent of filament)

| Calibration | Why It's Per-Printer | Redo When |
|-------------|---------------------|-----------|
| **Belt tension** | Physical frame property | Periodically, after moves, if ringing appears |
| **Input shaper** | Resonance of the frame/motion system | After belt/mechanical changes |
| **AUTO_SPEED / TEST_SPEED** | Motor/driver/belt capability | After mechanical changes |
| **Skew correction** | Frame squareness | After build, moves |
| **Cornering / junction deviation** | Motion system capability | After mechanical changes |
| **VFA test** | Stepper harmonics | After input shaper changes |
| **Elephant's foot compensation** | Z-offset + bed surface squish | After bed surface or Z-offset change |
| **Infill/perimeter overlap** | Nozzle geometry + extruder precision | After nozzle or extruder change |

---

## Phase 2: Filament Calibration (OrcaSlicer built-in tools)

Run these in order for each new filament. Results are saved to the filament profile and are valid across all process profiles (except PA — see above).

### 2.1 Rotation Distance (E-steps equivalent)

**What**: Verify extruder pushes exactly 100mm when told to push 100mm.
**When**: After any extruder hardware change. NOT per-filament.
**Scope**: Per-printer (hardware calibration).
**How**:

1. Heat nozzle to printing temp
2. Mark filament 120mm above extruder entry
3. `G91` → `G1 E100 F100`
4. Measure remaining distance from mark to entry
5. `new_rotation_distance = old_rotation_distance × (100 / actually_extruded)`

### 2.2 Temperature Tower

**What**: Find optimal nozzle temperature per filament.
**When**: Per filament brand/color. Even different colors of the same brand can differ.
**Scope**: Per-filament. Valid across all process profiles.
**Tool**: OrcaSlicer → Calibration → Temperature
- Tests: stringing, bridging, overhang, layer adhesion at each temp step
- Pick temp with best balance of all factors
- Save result to filament profile

**Speed printing note**: If you later create a speed-focused profile that pushes max volumetric flow, you may want a separate filament variant with +5-10°C to reduce viscosity at high flow. This is a deliberate choice, not a recalibration.

### 2.3 Max Volumetric Flow

**What**: Find max mm³/s before extruder skips/grinds.
**When**: Once per hotend + filament combination. Retest after nozzle change.
**Scope**: Per-hotend+filament. Valid across all process profiles (it's an absolute ceiling).
**Tool**: OrcaSlicer → Calibration → Max Volumetric Speed

1. Run the built-in test (prints lines at increasing flow rates)
2. Identify where quality degrades or extruder clicks/grinds
3. Set `filament_max_volumetric_speed` to 90% of that value
4. The slicer will auto-cap all speeds across all process profiles to respect this limit

### 2.4 Flow Rate

**What**: Fine-tune extrusion multiplier per filament.
**When**: Per filament brand/color.
**Scope**: Per-filament. Valid across all process profiles.
**Tool**: OrcaSlicer → Calibration → Flow Rate

1. Coarse calibration (prints single-wall box)
2. Measure wall thickness with calipers
3. Adjust flow ratio (target: wall thickness = exactly line_width)
4. Fine calibration (refine the result)
5. Save to filament profile

**Why it doesn't change with layer height**: The slicer already computes the geometric cross-section for each layer height. The flow ratio is a multiplier on top of that to compensate for filament diameter tolerance and material behavior. If you see underextrusion at extreme settings, the fix is adjusting max volumetric speed, not flow ratio.

### 2.5 Pressure Advance

**What**: Compensates for pressure buildup/release in the melt zone.
**When**: Per filament type. Ideally per filament brand.
**Scope**: Per-filament, but speed/accel-dependent (see scope section above).

**Option A: Static PA (OrcaSlicer pattern test)**
- OrcaSlicer → Calibration → Pressure Advance
- Visual comparison of line quality at different PA values
- Quick, one test print
- Good enough if you mostly use one process profile
- Save single PA value to filament profile

**Option B: Adaptive PA (recommended for multi-profile users)**
- OrcaSlicer → Calibration → Adaptive Pressure Advance
- Runs a matrix of tests: ~4 speeds × ~3 accelerations = 12 test prints
- OrcaSlicer builds a PA model and dynamically adjusts per-line
- Calibrate once → works across ALL process profiles (functional, miniature, prototype, etc.)
- Save model to filament profile

**Option C: Klipper TUNING_TOWER (classic)**
```
SET_VELOCITY_LIMIT SQUARE_CORNER_VELOCITY=1 ACCEL=500
TUNING_TOWER COMMAND=SET_PRESSURE_ADVANCE PARAMETER=ADVANCE START=0 FACTOR=.005
# Print square_tower.stl
# Direct drive: FACTOR=.005, range 0-0.1
# Bowden: FACTOR=.020, range 0-1.0
```

**Typical static PA ranges**:
| Extruder | Filament | PA Range |
|----------|----------|----------|
| Direct BMG | PLA | 0.02 - 0.08 |
| Direct BMG | PETG | 0.04 - 0.10 |
| Direct BMG | TPU | 0.00 - 0.02 |
| Bowden | PLA | 0.3 - 0.8 |
| Bowden | PETG | 0.4 - 1.0 |

### 2.6 Retraction Test

**What**: Optimize retraction length and speed to eliminate stringing.
**When**: Per filament type, after PA is set.
**Scope**: Per-filament + extruder type. Valid across all process profiles.
**Tool**: OrcaSlicer → Calibration → Retraction Test
- Direct drive: test 0.2-1.0mm in 0.1mm steps
- Bowden: test 2-8mm in 1mm steps
- Run AFTER PA calibration (PA reduces ooze pressure, so retraction needs less work)

### 2.7 Fan Speed Calibration

**What**: Find optimal minimum fan speed, maximum fan speed, and bridge fan speed for each filament.
**When**: Per filament type, after retraction is set.
**Scope**: Per-filament. Valid across all process profiles.

**Why it matters**: Too little cooling → curling on overhangs, bridges sag, fine detail deforms. Too much cooling → weak layer adhesion, delamination under stress, cracking (especially PETG/ABS).

**Procedure — Minimum Fan Speed (overhang test)**:
1. Print an overhang test (staircase from 15° to 75°)
2. Start with fan at 0%, increment by 10% per test
3. Find the lowest fan speed where overhangs at 45° don't curl upward
4. This is your `fan_min_speed` — used for normal printing

**Procedure — Maximum Fan Speed (snap test)**:
1. Print a single-wall rectangular tube (1 perimeter, no infill, 40mm tall)
2. Print at 100% fan, then reduce in 10% increments
3. Try to snap each test piece by bending — feel for layer adhesion
4. Maximum fan = highest speed where the piece still has good layer bond (doesn't snap cleanly between layers)

**Procedure — Bridge Fan Speed**:
1. Print a bridge test at your min fan speed — note sag
2. Increase fan speed for bridge sections only, in 10% increments
3. Bridge fan is typically 80-100% for PLA, 50-70% for PETG, 30-50% for ABS

**Typical ranges by material**:

| Material | Min Fan | Max Fan | Bridge Fan |
|----------|---------|---------|------------|
| PLA | 30-50% | 100% | 100% |
| PETG | 20-40% | 60-80% | 50-70% |
| ABS/ASA | 0-15% | 30-50% | 30-50% |
| TPU | 30-50% | 80-100% | 80-100% |

### 2.8 Minimum Layer Time

**What**: Minimum seconds per layer before the printer slows down or activates extra cooling. Prevents curling on small features (narrow columns, tips, small cross-sections) where the previous layer hasn't cooled before the next is deposited.
**When**: Per filament type, after fan speed is calibrated.
**Scope**: Per-filament. Valid across all process profiles.
**Tool**: Print a set of progressively smaller cylinders (e.g., 5mm, 10mm, 15mm diameter columns).

**Procedure**:
1. Start with minimum layer time at 5 seconds
2. Print a small column (5-8mm diameter, 40mm tall) at your normal speed
3. If the top curls/deforms, increase minimum layer time by 2 seconds
4. Repeat until the column prints cleanly
5. Typical result: 8-15 seconds for PLA, 10-20 seconds for PETG

**OrcaSlicer settings**:
- `slow_down_layer_time` — layer time threshold to trigger slowdown
- `fan_cooling_layer_time` — layer time threshold for max fan override
- Set `slow_down_layer_time` to your tested value
- Set `fan_cooling_layer_time` 2-3 seconds higher than `slow_down_layer_time`

### 2.9 Minimum Layer Speed

**What**: The minimum speed the printer will slow to when the minimum layer time constraint kicks in. Too slow → nozzle sits over deposited material and reheats it, causing deformation. Too fast → layer time constraint can't be met.
**When**: Per filament type, after minimum layer time is calibrated.
**Scope**: Per-filament. Valid across all process profiles.

**Procedure**:
1. Print the same small column from the min layer time test
2. Set minimum layer time to your calibrated value
3. Start with minimum speed at 10 mm/s
4. If the top still curls (nozzle reheating deposited plastic), increase min speed to 15, then 20 mm/s
5. If it doesn't slow down enough (layer time not met), decrease min speed
6. Sweet spot is typically 10-20 mm/s for PLA, 15-25 mm/s for PETG

**OrcaSlicer setting**: `slow_down_min_speed`

### 2.10 Bridge Flow Rate Calibration

**What**: Bridge-specific flow ratio — separate from normal extrusion flow. Bridges lay filament in free air; different flow rate prevents sag (too much) or gaps (too little).
**When**: Per filament AND per layer height. This is the per-process exception.
**Scope**: **Per-filament AND per-layer-height** — you WILL need to test this for every layer height profile you use. A bridge at 0.08mm behaves very differently from a bridge at 0.24mm.
**Tool**: Print a bridge test (two towers with bridge spans at increasing distances).

**Procedure**:
1. Print a bridge calibration model at your target layer height
2. Start with bridge flow ratio at 1.0 (100%)
3. Reduce by 0.05 increments: 0.95, 0.90, 0.85, 0.80, 0.75, 0.70
4. Examine each bridge: look for sag (flow too high) vs gaps/thinning (flow too low)
5. Typical results: 0.75-0.95 depending on layer height, material, and cooling

**Why layer height matters**: Thicker layers have more material weight per bridge strand. They sag more and need lower flow ratios. Thinner layers are lighter, cool faster, and tolerate higher flow ratios.

**Typical ranges**:

| Layer Height | PLA Bridge Flow | PETG Bridge Flow |
|-------------|----------------|-----------------|
| 0.08mm | 0.90-0.95 | 0.85-0.90 |
| 0.12mm | 0.85-0.95 | 0.80-0.90 |
| 0.20mm | 0.80-0.90 | 0.75-0.85 |
| 0.24mm | 0.75-0.85 | 0.70-0.80 |

**OrcaSlicer settings**: `bridge_flow` in the process profile (not the filament profile — because it's per-layer-height).

### 2.11 Material Shrinkage Compensation (optional, mainly ABS/ASA/Nylon)

**What**: Some materials shrink as they cool. For dimensionally critical parts, compensate by scaling the model.
**When**: Per filament type. Only necessary for materials with significant shrinkage (ABS ~0.4-0.7%, ASA ~0.4-0.7%, Nylon ~1-2%, PC ~0.5-0.7%). PLA and PETG shrinkage is negligible (<0.2%).
**Scope**: Per-filament. Valid across all process profiles for that material.

**Procedure**:
1. Print a reference cube (20x20x20mm, 100% infill for consistency)
2. Let it cool completely to room temperature (wait at least 1 hour)
3. Measure all three axes with calipers
4. Compute scale factor: `scale = 20.0 / measured_dimension`
5. Apply XY and Z compensation in OrcaSlicer filament profile
6. Re-print and verify

**OrcaSlicer settings**:
- `shrinkage_compensation_xy` — XY percentage compensation (e.g., 100.5% = 0.5% expansion to compensate shrinkage)
- `shrinkage_compensation_z` — Z percentage compensation

**Skip for PLA/PETG** unless the user is printing dimensionally critical mating parts.

---

## Phase 3: Validation & Fine-Tuning

### 3.1 Tolerance / Dimensional Accuracy

**What**: Verify printed dimensions match design.
**When**: After all above calibrations are done. Once per printer.
**Scope**: Per-printer. Valid across filaments and process profiles.
**Tool**: OrcaSlicer → Calibration → Tolerance Test
- Prints a gauge with different gaps
- Measure with calipers

### 3.2 VFA Test (Vertical Fine Artifacts)

**What**: Detect stepper motor harmonic artifacts on vertical surfaces.
**When**: After input shaper changes, or if you see regular vertical patterns.
**Scope**: Per-printer.
**Tool**: OrcaSlicer → Calibration → VFA Test

### 3.3 Validation Prints

**What**: Full test prints that exercise multiple features at once — the final check after all calibration is complete.
**When**: After completing per-filament calibration for a new material, or after significant config changes.
**Scope**: Per-filament validation.

**Recommended validation models**:

1. **Voron Calibration Cube** — Tests dimensional accuracy, corner sharpness (PA), top/bottom surface quality, layer consistency. Print one per filament.
   - Measure: 20.0mm ± 0.1mm on all axes
   - Inspect: corners sharp (not rounded = PA good), top surface smooth (flow good), no ringing (input shaper good)

2. **Cali Dragon** (or similar complex model) — Tests overhangs, bridging, fine detail, retraction (teeth/spines), and cooling all in one print. This is the "real world" validation.
   - Inspect: clean overhangs, no stringing between spines, bridges don't sag, fine detail is crisp

3. **Benchy** (classic) — Good general-purpose test but less targeted than the above two.

**Workflow**: Print Voron cube first (quick, 20-30 min). If it passes dimensional checks, print Cali Dragon (1-2 hours). If both look good, your calibration is complete.

### 3.4 Temperature Test Alternative: Hand-Push Method

**What**: A quick, intuitive way to find the right printing temperature without a temperature tower. Useful when you want a rough starting point fast.
**When**: Optional alternative to the temperature tower (2.2). Good for experienced users who want a quick ballpark.

**Procedure**:
1. Unlatch the extruder (release tension on the filament drive gear)
2. Heat the nozzle to the low end of the filament's range (e.g., 190°C for PLA)
3. Push the filament by hand through the hotend
4. Feel the resistance — it should be moderate and consistent
5. Increase temperature by 5°C increments
6. At some point you'll feel the resistance drop noticeably — the filament flows more easily
7. That temperature ± 5°C is a good starting point
8. If you can barely push it through → too cold
9. If it flows with almost no resistance and drips → too hot

**Limitations**: This is subjective and doesn't test bridging, layer adhesion, or stringing like a temperature tower does. Use it for a quick starting point, then validate with actual prints.

---

## Per-Filament Calibration Checklist

When the user adds a new filament, guide them through this sequence:

```
New filament arrived
  │
  ├─ 1. Temperature tower              (~30 min print)
  │     Save: nozzle temp → filament profile
  │     Alt: hand-push method for quick ballpark (see 3.4)
  │
  ├─ 2. Max volumetric flow            (~20 min print)
  │     Save: filament_max_volumetric_speed ��� filament profile
  │
  ├─ 3. Pressure advance               (~20 min static, ~2 hrs adaptive)
  │     Save: PA value or adaptive model → filament profile
  │     ★ Use Adaptive PA if user prints with multiple process profiles
  │
  ├─ 4. Flow rate (coarse + fine)      (~40 min, 2 prints)
  │     Save: flow ratio �� filament profile
  │     ⚠ If flow ratio is >10% off (>1.10 or <0.90), REDO step 3 (PA)
  │
  ├─ 5. Retraction test                (~20 min print)
  │     Save: retraction length → filament profile
  │
  ├─ 6. Fan speed calibration          (~1 hr, 3 tests)
  │     Save: min fan, max fan, bridge fan → filament profile
  │     a. Overhang test → min fan speed
  │     b. Snap test → max fan speed
  │     c. Bridge fan test → bridge fan speed
  │
  ├─ 7. Minimum layer time             (~30 min)
  │     Save: slow_down_layer_time → filament profile
  │     Print small columns, increment by 2s until clean
  │
  ├─ 8. Minimum layer speed            (~30 min)
  │     Save: slow_down_min_speed → filament profile
  │     Find sweet spot: cooling works but nozzle doesn't reheat deposited filament
  │
  ├─ 9. Bridge flow rate               (~20 min PER LAYER HEIGHT)
  │     Save: bridge_flow → process profile (NOT filament)
  │     ★ This is the ONE per-process calibration — repeat for each layer height
  │
  ├─ 10. Shrinkage compensation        (optional, ~30 min)
  │      Save: shrinkage_compensation_xy/z → filament profile
  │      ★ Skip for PLA/PETG. Required for ABS/ASA/Nylon/PC.
  │
  └─ 11. Validation prints             (~1.5 hrs)
         a. Voron calibration cube (~20 min) — dimensional check
         b. Cali Dragon (~1 hr) — overhangs, bridges, detail, retraction

Total: ~4-5 hours for full calibration (~6 hours with Adaptive PA)
Steps 1-5 are critical and non-negotiable.
Steps 6-8 are important for quality — skip only if pressed for time.
Step 9 is per-process — do once per layer height you actually use.
Step 10 is optional for PLA/PETG, required for ABS/ASA/Nylon.
Step 11 validates everything — always do this.
After steps 1-8, the filament is calibrated for ALL process profiles (except bridge flow).
```

---

## Quick Reference: What to Re-Calibrate After Changes

| Change Made | Re-Calibrate |
|------------|-------------|
| Re-tensioned belts | Input shaper → AUTO_SPEED |
| New belt / replaced belt | Belt tension → Input shaper → AUTO_SPEED |
| New stepper motor | Belt tension (verify) → Input shaper → AUTO_SPEED → rotation distance (if extruder) |
| New hotend | Volumetric flow → temperature tower → PA → flow rate → retraction → fan speed |
| New nozzle (same size) | Temperature tower → PA (verify) |
| New nozzle (different size) | Volumetric flow → all filament calibrations |
| New filament brand | Temperature tower → volumetric flow → PA → flow rate → retraction → fan speed → min layer time → min layer speed → validate |
| New filament type | Full sequence: temp → vol. flow → PA → flow → retraction → fan speed → min layer time → min layer speed → bridge flow → shrinkage → validate |
| Firmware update | Input shaper (verify) → PA (verify) |
| Changed acceleration | PA (verify — PA interacts with accel) |
| Moved printer | Belt tension (verify) → Input shaper → skew correction |
| Changed extruder gear | Rotation distance → PA → flow rate |
| Ringing/ghosting appeared | Belt tension → Input shaper |
| Layer shifts | Belt tension → stepper current → AUTO_SPEED (lower limits) |
| Changed bed surface | Elephant's foot compensation → first layer settings |
| Changed Z-offset | Elephant's foot compensation (verify) |
| New layer height profile | Bridge flow rate calibration (per-process) |
| Flow ratio corrected by >10% | Re-do PA calibration |
| Curling on small features | Min layer time → min layer speed → fan speed |
| Bridges sagging | Bridge flow rate → bridge fan speed → bridge speed |
