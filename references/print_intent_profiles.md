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
Priorities: fine detail, thin features, tiny overhangs, smooth top surfaces.
Key settings: very low layer height, low speed, low accel, ironing, many top layers.
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
| Layer height | 0.20 | 0.12 | 0.08 | 0.24 | 0.20 | 0.20 |
| Outer wall | 80 | 40 | 25 | 120 | 25 | 60 |
| Inner wall | 120 | 60 | 40 | 180 | 30 | 80 |
| Infill | 150 | 80 | 60 | 200 | 40 | 100 |
| Top surface | 60 | 30 | 20 | 80 | 20 | 40 |
| Travel | 200 | 150 | 120 | 250 | 80 | 150 |
| First layer | 30 | 20 | 15 | 40 | 15 | 25 |
| Bridge | 25 | 20 | 15 | 30 | 15 | 20 |

## Per-Intent Accel Matrix (before hardware clamping)

| Setting | Functional | Visual | Miniature | Prototype | Wearable | Structural |
|---------|-----------|--------|-----------|-----------|----------|------------|
| Default | 3000 | 1500 | 1000 | 5000 | 1000 | 2000 |
| Outer wall | 1500 | 800 | 500 | 2500 | 500 | 1000 |
| Inner wall | 3000 | 1500 | 1000 | 5000 | 1000 | 2000 |
| Top surface | 1500 | 800 | 500 | 2500 | 500 | 1000 |
| Travel | 3000 | 2000 | 1500 | 5000 | 1000 | 2000 |
| First layer | 500 | 500 | 300 | 500 | 300 | 500 |

## Per-Intent Structure Matrix

| Setting | Functional | Visual | Miniature | Prototype | Wearable | Structural |
|---------|-----------|--------|-----------|-----------|----------|------------|
| Walls | 3 | 3 | 3 | 2 | 4 | 5 |
| Top layers | 4 | 5 | 6 | 3 | 4 | 5 |
| Bottom layers | 3 | 4 | 5 | 3 | 3 | 5 |
| Infill % | 25% | 15% | 15% | 10% | 15% | 50% |
| Infill pattern | gyroid | grid | grid | grid | gyroid | cubic |
| Seam | nearest | aligned | aligned | nearest | nearest | nearest |
| Ironing | no | no | top | no | no | no |
| Bridge flow | 0.95 | 0.90 | 0.85 | 1.0 | 1.0 | 0.95 |

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
- Enabled for all intents (better thin wall handling)
- Especially important for miniature and visual intents

### Arc fitting
- Enabled for all intents if `[gcode_arcs]` is in Klipper config
- Reduces gcode file size and improves curve smoothness

### Detect thin wall
- Enabled for all intents
- Critical for miniature intent (tiny features)
