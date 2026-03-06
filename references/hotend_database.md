# Hotend Database — Volumetric Flow Limits

Flow rates are for 0.4mm brass nozzle with PLA at ~210°C unless noted.
Actual flow varies with filament, temperature, and nozzle size.

Scale factor for nozzle sizes (approximate):
- 0.25mm nozzle: flow × 0.4
- 0.4mm nozzle: flow × 1.0 (baseline)
- 0.6mm nozzle: flow × 1.8
- 0.8mm nozzle: flow × 2.5

## All-Metal Hotends

| Hotend | Max Flow (mm³/s) | Max Temp (°C) | Heatbreak | Notes |
|--------|-----------------|---------------|-----------|-------|
| **Creality Spider 3 Pro** | 15-18 | 300 | Bi-metal titanium | Good for modded Enders |
| **E3D V6** | 11-14 | 285 | All-metal or PTFE | Classic, well-documented |
| **E3D Revo Six** | 12-15 | 300 | Quick-change nozzle system | Easy nozzle swaps |
| **E3D Revo Voron** | 12-15 | 300 | Designed for Voron | Same internals as Revo Six |
| **Phaetus Dragon Standard** | 15-18 | 500 | Bi-metal | Popular Voron upgrade |
| **Phaetus Dragon High Flow** | 22-28 | 500 | Bi-metal, wider melt zone | For speed printing |
| **Phaetus Dragonfly BMO** | 14-17 | 500 | Bi-metal | Compact, V6 mount |
| **Phaetus Rapido** | 25-32 | 350 | UHF, ceramic heater | Very fast |
| **Phaetus Rapido 2** | 30-38 | 350 | UHF, improved | Current king of flow |
| **Slice Engineering Mosquito** | 14-17 | 500 | All-metal | Premium build quality |
| **Slice Mosquito Magnum+** | 25-30 | 500 | High flow variant | Expensive |
| **Bambu Lab hotend** | 24-32 | 300 | Bi-metal, ceramic heater | Proprietary, P1/X1 series |
| **TriangleLab TZ V6** | 12-15 | 300 | Bi-metal | V6 clone, good value |
| **TriangleLab CHC Pro** | 18-22 | 300 | Ceramic heater, bi-metal | Fast heat-up |
| **Mellow NF-Zone** | 14-17 | 500 | Bi-metal copper | V6 compatible |
| **Brozzl All-Metal** | 11-14 | 300 | All-metal | Budget upgrade |

## PTFE-Lined Hotends

| Hotend | Max Flow (mm³/s) | Max Temp (°C) | Notes |
|--------|-----------------|---------------|-------|
| **Creality stock (MK8)** | 8-11 | 240 (PTFE limit) | Stock Ender 3 |
| **Creality Sprite** | 10-13 | 260 | Ender 3 S1/V3 stock |
| **E3D Lite6** | 10-12 | 240 (PTFE limit) | Budget E3D |
| **Prusa MK3S stock** | 10-13 | 285 | E3D V6 variant |

## Volcano-Style (Extended Melt Zone)

| Hotend | Max Flow (mm³/s) | Max Temp (°C) | Notes |
|--------|-----------------|---------------|-------|
| **E3D Volcano** | 20-25 | 285 | Original extended melt zone |
| **Phaetus Dragon UHF** | 22-28 | 500 | Ultra high flow, long melt path |
| **Slice Mosquito Magnum** | 20-25 | 500 | Extended melt zone Mosquito |
| **Bondtech CHT** | +30-50% over base | varies | CHT nozzle on any hotend |

## Flow Rate Adjustment by Filament

Multiplier relative to PLA baseline:

| Filament | Flow Multiplier | Reason |
|----------|----------------|--------|
| PLA | 1.0× | Baseline — flows easily |
| PETG | 0.75× | Higher viscosity |
| TPU | 0.3× | Very viscous, compresses |
| ABS | 0.85× | Slightly more viscous than PLA |
| ASA | 0.80× | Similar to ABS |
| Nylon | 0.70× | High viscosity |
| PC | 0.65× | Very viscous |
| SILK PLA | 0.85× | Additives increase viscosity slightly |
| CF-PLA | 0.80× | Carbon fiber increases drag |
| CF-PETG | 0.60× | Carbon fiber + viscosity |

## Nozzle Material Effects

| Material | Flow Effect | Temperature Limit | Wear Resistance | Best For |
|----------|------------|-------------------|-----------------|----------|
| Brass | Baseline | 300°C | Low | PLA, PETG, TPU |
| Hardened Steel | -10-15% flow | 450°C | High | CF, GF filaments |
| Stainless Steel | -5-10% flow | 400°C | Medium | Food-safe, some abrasives |
| Ruby tip | -5% flow | 450°C | Very high | Abrasive filaments |
| Tungsten Carbide | -5% flow | 500°C | Extreme | Most abrasive filaments |
| CHT (any material) | +30-50% flow | varies | varies | Speed printing, thick layers |

## How to Use This Data

1. Look up user's hotend model → get PLA flow rate at 0.4mm
2. Apply filament multiplier for their material
3. Apply nozzle size scale factor if not 0.4mm
4. Apply nozzle material penalty if not brass
5. Result = max volumetric flow for `filament_max_volumetric_speed`
6. This limits effective speed: `max_speed = flow / (layer_height × line_width)`

### Example
Spider 3 Pro (17 mm³/s) + PETG (0.75×) + 0.4mm brass:
→ 17 × 0.75 = 12.75 mm³/s
→ At 0.20mm layer, 0.44mm width: max speed = 12.75 / (0.20 × 0.44) = 145 mm/s
