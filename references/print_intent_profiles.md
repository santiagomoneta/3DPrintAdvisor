# Print Intent → Settings Matrix

## Intent Definitions

### Functional
Parts that need to work: brackets, mounts, enclosures, jigs, fixtures, clips.
Priorities: dimensional accuracy, layer adhesion, reasonable speed.
Not concerned about: surface finish on non-visible faces, minor ringing.

### Visual / Display
Parts people will look at: vases, decorations, gifts, display models.
Priorities: smooth surfaces, no blobs or zits, clean seams, no ringing.
Not concerned about: print time, structural strength.

### Miniature / Figurine
Small detailed parts: tabletop minis, anime figures, detailed sculptures.
Priorities: fine detail, thin features, tiny overhangs, smooth surfaces.
Key hardware: 0.2mm nozzle strongly recommended — 0.4mm loses fine detail.
Key settings: 0.06mm layer height (optimal balance), classic wall generator (not Arachne), inner-outer-inner wall sequence, very low speeds, stepped overhang slowdowns, gyroid infill, scarf seam, tree supports with correct tip diameter.
Not concerned about: print time (these are commitment prints).

### Prototype / Draft
Just need the shape fast: test fits, spatial checks, design validation.
Priorities: speed, speed, speed. Minimum acceptable quality.
Not concerned about: surface finish, strength, fine detail.

### Wearable / Flexible
TPU/flex parts: phone cases, watch bands, gaskets, hinges.
Priorities: even extrusion (no retraction artifacts), good layer adhesion, flex without delamination.
Key settings: slow everything, minimal or no retraction, lower accel.

### Structural / Load-Bearing
Parts under load: gears, pulleys, tooling, stressed brackets.
Priorities: maximum layer adhesion, high wall count, dense infill, strength.
Key settings: more walls, more infill, moderate speed for good bonding.

---

## Per-Intent Speed Matrix (before hardware clamping)

| Setting | Functional | Visual | Miniature | Prototype | Wearable | Structural |
|---------|-----------|--------|-----------|-----------|----------|------------|
| Layer height | 0.20 | 0.12 | 0.06 | 0.24 | 0.20 | 0.20 |
| Outer wall | 80 | 40 | 35 | 120 | 25 | 60 |
| Inner wall | 120 | 60 | 55 | 180 | 30 | 80 |
| Infill | 150 | 80 | 65 | 200 | 40 | 100 |
| Top surface | 60 | 30 | 35 | 80 | 20 | 40 |
| Travel | 200 | 150 | 120 | 250 | 80 | 150 |
| First layer | 30 | 20 | 15 | 40 | 15 | 25 |
| Bridge | 25 | 20 | 15 | 30 | 15 | 20 |

## Per-Intent Accel Matrix (before hardware clamping)

| Setting | Functional | Visual | Miniature | Prototype | Wearable | Structural |
|---------|-----------|--------|-----------|-----------|----------|------------|
| Default | 3000 | 1500 | 2000 | 5000 | 1000 | 2000 |
| Outer wall | 1500 | 800 | 1000 | 2500 | 500 | 1000 |
| Inner wall | 3000 | 1500 | 2000 | 5000 | 1000 | 2000 |
| Top surface | 1500 | 800 | 1000 | 2500 | 500 | 1000 |
| Travel | 3000 | 2000 | 1500 | 5000 | 1000 | 2000 |
| First layer | 500 | 500 | 300 | 500 | 300 | 500 |

## Per-Intent Structure Matrix

| Setting | Functional | Visual | Miniature | Prototype | Wearable | Structural |
|---------|-----------|--------|-----------|-----------|----------|------------|
| Walls | 3 | 3 | 3 | 2 | 4 | 5 |
| Top layers | 4 | 5 | 6 | 3 | 4 | 5 |
| Bottom layers | 3 | 4 | 5 | 3 | 3 | 5 |
| Infill % | 25% | 15% | 20% | 10% | 15% | 50% |
| Infill pattern | gyroid | grid | gyroid | grid | gyroid | cubic |
| Seam | nearest | aligned | scarf | nearest | nearest | nearest |
| Ironing | no | no | top | no | no | no |
| Bridge flow | 0.95 | 0.90 | 0.85 | 1.0 | 1.0 | 0.95 |

> **Bridge flow is per-layer-height**: The values above are defaults for each intent's standard layer height. Bridge flow varies significantly with layer height — thicker layers sag more and need lower flow ratios. If you change the layer height for a given intent, re-calibrate bridge flow. See `calibration_toolkit.md` §2.10 for the full procedure and per-layer-height reference table.

## Fan Speed Defaults by Intent

| Setting | Functional | Visual | Miniature | Prototype | Wearable | Structural |
|---------|-----------|--------|-----------|-----------|----------|------------|
| Min fan % | 40 | 50 | 60 | 30 | 40 | 30 |
| Max fan % | 100 | 100 | 100 | 100 | 100 | 80 |
| Bridge fan % | 100 | 100 | 100 | 80 | 80 | 80 |
| Min layer time (s) | 10 | 12 | 15 | 6 | 10 | 8 |
| Slow down min speed | 15 | 10 | 8 | 20 | 10 | 15 |

> These are PLA defaults. PETG: reduce all fan speeds by 20-30%. ABS/ASA: reduce to 0-40%. TPU: similar to PLA. These should be overridden by actual per-filament calibration results when available.

## Filament Adjustments by Intent

### PLA
- All intents work well with PLA
- Miniature: consider dropping nozzle temp by 5°C to reduce oozing on fine detail
- Prototype: can push volumetric flow to limit

### PETG
- Visual: reduce outer wall speed by 20% (PETG strings more at speed)
- Miniature: not ideal — PETG lacks fine-detail capability due to stringing
- Structural: excellent choice — best layer adhesion of easy filaments
- Always: slightly lower retraction to avoid clogs in all-metal hotend

### TPU
- Forces wearable intent settings regardless of user choice (TPU can't go fast)
- Zero or near-zero retraction for direct drive
- No retraction at all for bowden
- Reduce travel speed significantly (flex filament column bucks at high accel)

### ABS/ASA (enclosure required)
- Not recommended without enclosure (warping, layer splitting)
- If user insists with no enclosure: warn, small parts only, brim on everything
- Draft/brim strongly recommended for all intents
- Lower fan speeds across the board (15-40%)

## Special Features by Intent

### Ironing (miniature only by default)
- Speed: 15 mm/s
- Flow: 10%
- Only top surfaces
- Adds significant print time but dramatically improves top surface quality
- User can request ironing on any intent

### Arachne wall generator
- Enabled for all intents **except miniature**
- For miniature intent: use **Classic** wall generator — fewer edge-case artifacts at small scales with fine geometry
- Especially important for visual intent (better thin wall handling)

### Arc fitting
- Enabled for all intents if `[gcode_arcs]` is in Klipper config
- Reduces gcode file size and improves curve smoothness

### Detect thin wall
- Enabled for all intents
- Critical for miniature intent (tiny features)

---

## Miniature Support Settings

These settings are critical for miniature printing — wrong values cause supports to fuse to the model.

| Setting | Value | Notes |
|---------|-------|-------|
| `support_type` | `tree(auto)` | Organic/grid style, NOT slim |
| `support_style` | `default` | Slim style skips interface generation |
| `support_threshold_angle` | `15°` | Conservative; increase to 20–25° if spaghetti, max 30° |
| `support_top_z_distance` | multiple of layer_height | 0.06mm layers → 0.18mm; 0.08mm → 0.24mm; 0.12mm → 0.12mm |
| `support_bottom_z_distance` | `0mm` | |
| `support_interface_spacing` | `0.2mm` | |
| `support_base_pattern` | `rectilinear-grid` | |
| `support_base_pattern_spacing` | `3mm` | |
| `tree_support_tip_diameter` | `1.2mm` | **CRITICAL**: values below 1.0mm suppress interface generation, causing supports to fuse directly to the model. If support interface (dark green in preview) is missing, increase this value. |
| `tree_support_branch_diameter` | `1.0mm` | |
| `tree_support_branch_distance` | `1.0mm` | |
| `tree_support_wall_count` | `2` | |
| `support_on_build_plate_only` | `true` | |
| `bridge_flow` | `0.85` | |
| `internal_bridge_flow` | `0.85` | |
| `thick_internal_bridges` | `false` | |

## Miniature Workflow Tips

- **Split complex models into parts** and orient each piece to minimize overhangs — bigger impact than any setting change
- **Orientation first**: maximize flat base area, rotate arms/weapons to reduce unsupported angles
- **Filament calibration** (flow ratio, PA, temperature) has more quality impact than going from 0.06mm to 0.05mm layers
- **Dry filament**: 8h at 50°C for PLA before printing — moisture causes surface defects at 0.06mm layers
- **Recommended filaments**: eSun PLA+ HS (better overhangs), Sunlu PLA+ 2.0 HS (better surface quality)
- **Ironing**: off by default for miniatures (few flat surfaces); enable only for vehicles/terrain with large flat tops
- **If nozzle hits print**: disable `reduce_infill_retraction` first — most common cause
- **If support trees fall over**: check first layer adhesion — tree supports need a solid anchor
- **If support interface is missing** in preview (dark green layer absent): increase `tree_support_tip_diameter`

> **Source:** "Dungeons and Derps" HQ Profile v2.0 by u/ObscuraNox
> ([r/FDMminiatures](https://www.reddit.com/r/FDMminiatures/comments/1rbnet7/high_quality_profile_version_20_is_here/)) —
> settings and rationale extracted from the v2.0 JSON profile and full documentation post.
