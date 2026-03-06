# Calibration Toolkit — Complete Workflow

## Calibration Order

Always calibrate in this order. Each step depends on the previous ones being correct.

```
0. Belt Tension  →  1. Mechanical     →  2. Extrusion     →  3. Print Quality
   (physical)        (frame/motion)       (flow/PA)           (per-filament)
```

Belt tension is step zero because it has no software component — it's a physical prerequisite that affects every subsequent calibration. Get belts right first, then everything else builds on a solid foundation.

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

These are stable across process profiles. A PLA spool wants the same temperature and flow ratio whether you print at 0.08mm miniature or 0.24mm prototype layer height.

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

---

## Per-Filament Calibration Checklist

When the user adds a new filament, guide them through this sequence:

```
New filament arrived
  │
  ├─ 1. Temperature tower          (~30 min print)
  │     Save: nozzle temp → filament profile
  │
  ├─ 2. Max volumetric flow        (~20 min print)
  │     Save: filament_max_volumetric_speed → filament profile
  │
  ├─ 3. Flow rate (coarse + fine)  (~40 min, 2 prints)
  │     Save: flow ratio → filament profile
  │
  ├─ 4. Pressure advance           (~20 min for static, ~2 hrs for adaptive)
  │     Save: PA value or adaptive model → filament profile
  │     ★ Use Adaptive PA if user prints with multiple process profiles
  │
  └─ 5. Retraction test            (~20 min print)
        Save: retraction length → filament profile

Total: ~2.5 hours for full calibration (~4 hours with Adaptive PA)
After this, the filament is calibrated for ALL process profiles.
```

---

## Quick Reference: What to Re-Calibrate After Changes

| Change Made | Re-Calibrate |
|------------|-------------|
| Re-tensioned belts | Input shaper → AUTO_SPEED |
| New belt / replaced belt | Belt tension → Input shaper → AUTO_SPEED |
| New stepper motor | Belt tension (verify) → Input shaper → AUTO_SPEED → rotation distance (if extruder) |
| New hotend | Volumetric flow → temperature tower → PA → retraction → flow rate |
| New nozzle (same size) | Temperature tower → PA (verify) |
| New nozzle (different size) | Volumetric flow → all print quality tests |
| New filament brand | Temperature tower → PA → retraction → flow rate |
| New filament type | PA → temperature tower → retraction → flow rate → volumetric flow |
| Firmware update | Input shaper (verify) → PA (verify) |
| Changed acceleration | PA (verify — PA interacts with accel) |
| Moved printer | Belt tension (verify) → Input shaper → skew correction |
| Changed extruder gear | Rotation distance → PA → flow rate |
| Ringing/ghosting appeared | Belt tension → Input shaper |
| Layer shifts | Belt tension → stepper current → AUTO_SPEED (lower limits) |
