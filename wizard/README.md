# OrcaSlicer Printer Setup Wizard

A local web app that walks you through setting up a custom Klipper printer in OrcaSlicer — no config editing required.

## What it does

1. **Connects** to your Moonraker server and auto-detects printer limits (max velocity, accel, nozzle, PA)
2. **Asks** about your hardware mods (hotend, extruder type, cooling, enclosure, build volume)
3. **Asks** what you print (miniatures, functional parts, visual models, prototypes, structural, TPU)
4. **Generates** ready-to-use OrcaSlicer machine + process + filament profiles
5. **Copies** them directly into your OrcaSlicer profile directory — just restart OrcaSlicer

## Install & run

```bash
pip install -r wizard/requirements.txt
python wizard/app.py
```

Opens automatically at http://127.0.0.1:7860

## Requirements

- Python 3.8+
- OrcaSlicer installed locally
- Klipper + Moonraker (optional — you can skip and enter specs manually)

## Generated profiles

Profiles land in `output/` and are copied to your OrcaSlicer user directory:

```
output/
├── machine/   ← printer profile (speeds, build volume, G-code)
├── process/   ← one profile per selected intent (layer height, speeds, supports)
└── filament/  ← filament profile (temps, fan, PA — calibrate these afterward!)
```

## After setup

1. Restart OrcaSlicer — your new printer appears in the printer dropdown
2. Run filament calibrations: **Temperature → Flow Rate → Pressure Advance**
3. For miniatures: confirm your 0.2mm nozzle is installed
4. Print a test model before committing to long prints

## Print intents

| Intent | Layer height | Use case |
|--------|-------------|----------|
| Miniatures | 0.06mm | Tabletop minis, figurines (0.2mm nozzle recommended) |
| Functional | 0.20mm | Brackets, mounts, enclosures |
| Visual | 0.12mm | Display pieces, decorations |
| Prototype | 0.24mm | Fast test fits |
| Structural | 0.20mm | Load-bearing parts, gears |
| Wearable/TPU | 0.20mm | Flexible parts, phone cases |
