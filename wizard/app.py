#!/usr/bin/env python3
"""
OrcaSlicer Printer Setup Wizard
A Gradio web app that walks you through setting up a custom Klipper printer
in OrcaSlicer — asking about your hardware, mods, and print intent, then
generating ready-to-use machine + process profiles.

Usage:
    pip install -r requirements.txt
    python wizard/app.py
"""

import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
import gradio as gr

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
STATE_DIR = REPO_ROOT / "state"
OUTPUT_DIR = REPO_ROOT / "output"
STATE_FILE = STATE_DIR / "profile_context.json"

STATE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _run_script(script, *args, input_json=None):
    """Run a shell/python script from the scripts/ directory."""
    cmd = [
        sys.executable if script.endswith(".py") else "bash",
        str(SCRIPTS_DIR / script),
        *args,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_moonraker(url: str):
    """Try to reach Moonraker and return a status string."""
    url = url.strip().rstrip("/")
    if not url:
        return "⚠️ Please enter a Moonraker URL first.", None

    try:
        import urllib.request

        req = urllib.request.urlopen(f"{url}/printer/info", timeout=5)
        data = json.loads(req.read())
        hostname = data.get("result", {}).get("hostname", "unknown")
        state = data.get("result", {}).get("state", "unknown")
        return f"✅ Connected — hostname: **{hostname}**, state: **{state}**", url
    except Exception as e:
        return f"❌ Could not connect: {e}", None


def fetch_klipper_config(url: str):
    """Fetch printer limits from Moonraker and return a summary dict."""
    try:
        import urllib.request

        req = urllib.request.urlopen(
            f"{url}/printer/objects/query?configfile", timeout=10
        )
        raw = json.loads(req.read())
        cfg = (
            raw.get("result", {})
            .get("status", {})
            .get("configfile", {})
            .get("config", {})
        )

        printer_sec = cfg.get("printer", {})
        extruder_sec = cfg.get("extruder", {})
        shaper_sec = cfg.get("input_shaper", {})

        return {
            "max_velocity": float(printer_sec.get("max_velocity", 300)),
            "max_accel": float(printer_sec.get("max_accel", 3000)),
            "nozzle_diameter": float(extruder_sec.get("nozzle_diameter", 0.4)),
            "pressure_advance": float(extruder_sec.get("pressure_advance", 0.05)),
            "input_shaper": {
                "x": {
                    "type": shaper_sec.get("shaper_type_x", "mzv"),
                    "freq": float(shaper_sec.get("shaper_freq_x", 0)),
                },
                "y": {
                    "type": shaper_sec.get("shaper_type_y", "mzv"),
                    "freq": float(shaper_sec.get("shaper_freq_y", 0)),
                },
            },
        }
    except Exception:
        return {}


def detect_orcaslicer_profile_dir():
    """Find OrcaSlicer user profile directory on Windows/macOS/Linux."""
    import platform

    system = platform.system()
    candidates = []

    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        candidates.append(Path(appdata) / "OrcaSlicer" / "user")
    elif system == "Darwin":
        candidates.append(
            Path.home() / "Library" / "Application Support" / "OrcaSlicer" / "user"
        )
    else:
        candidates.append(Path.home() / ".config" / "OrcaSlicer" / "user")

    for base in candidates:
        if base.exists():
            # Prefer logged-in account dir (numeric subdirectory)
            for child in base.iterdir():
                if child.is_dir() and child.name.isdigit():
                    return str(child)
            default = base / "default"
            if default.exists():
                return str(default)
    return None


def build_context(
    moonraker_url,
    printer_name,
    kinematics,
    build_x,
    build_y,
    build_z,
    nozzle_diameter,
    extruder_type,
    hotend_model,
    cooling,
    enclosure,
    klipper_data,
):
    """Assemble profile_context.json from wizard answers."""
    nozzle = float(nozzle_diameter.replace("mm", "").strip())
    bx, by, bz = float(build_x), float(build_y), float(build_z)

    # Estimate Y accel limit for bed-slingers
    y_accel_limit = None
    if kinematics == "Cartesian (bed-slinger)":
        y_accel_limit = min(klipper_data.get("max_accel", 3000), 2500)

    # Estimate volumetric flow from hotend
    flow_map = {
        "Stock PTFE (Creality/Ender)": 8,
        "All-Metal (Creality/Ender)": 12,
        "E3D V6": 14,
        "Dragon / Rapido / Dragonfly": 20,
        "Volcano / High-Flow": 30,
        "Bambu stock": 35,
        "Other": 12,
    }
    vol_flow = flow_map.get(hotend_model, 12)

    return {
        "version": 1,
        "environment": {
            "os": sys.platform,
            "orcaslicer_profile_dir": detect_orcaslicer_profile_dir() or "",
        },
        "printer": {
            "name": printer_name.strip() or "My Klipper Printer",
            "kinematics": kinematics,
            "build_volume": {"x": bx, "y": by, "z": bz},
            "moonraker_url": moonraker_url,
            "hotend": {"model": hotend_model, "max_flow_mm3s": vol_flow},
            "extruder": {"type": extruder_type},
            "nozzle": {"diameter": nozzle, "material": "brass"},
            "cooling": cooling,
            "enclosure": enclosure == "Yes",
        },
        "klipper": {
            "max_velocity": klipper_data.get("max_velocity", 300),
            "max_accel": klipper_data.get("max_accel", 3000),
            "pressure_advance": klipper_data.get("pressure_advance", 0.05),
            "input_shaper": klipper_data.get("input_shaper", {}),
        },
        "bottlenecks": {
            "y_accel_limit": y_accel_limit,
            "volumetric_flow_limit": vol_flow,
        },
        "filaments": ["PLA"],
        "generated_profiles": [],
    }


def generate_profiles(ctx: dict, intents: list, filament: str):
    """Write context to disk and call generate_profile.py for each intent."""
    STATE_FILE.write_text(json.dumps(ctx, indent=2))

    results = []
    for intent in intents:
        stdout, stderr, code = _run_script(
            "generate_profile.py",
            "--context",
            str(STATE_FILE),
            "--intent",
            intent,
            "--filament",
            filament,
            "--output-dir",
            str(OUTPUT_DIR),
        )
        if code == 0:
            try:
                generated = json.loads(stdout)
                results.extend(generated)
            except Exception:
                results.append({"intent": intent, "error": stderr or stdout})
        else:
            results.append({"intent": intent, "error": stderr or stdout})

    return results


def copy_to_orcaslicer(results: list, profile_dir: str):
    """Copy generated profiles to OrcaSlicer user directory."""
    if not profile_dir or not Path(profile_dir).exists():
        return "❌ OrcaSlicer profile directory not found. Copy files manually from `output/`."

    copied = []
    for item in results:
        src = Path(item.get("path", ""))
        if not src.exists():
            continue
        profile_type = item.get("type", "process")
        dest_dir = Path(profile_dir) / profile_type
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        dest.write_bytes(src.read_bytes())
        copied.append(str(dest))

        # Copy paired .info file if it exists
        info_src = src.with_suffix(".info")
        if info_src.exists():
            info_dest = dest_dir / info_src.name
            info_dest.write_bytes(info_src.read_bytes())

    if copied:
        return (
            f"✅ Copied {len(copied)} files to OrcaSlicer. **Restart OrcaSlicer** to see them.\n\n"
            + "\n".join(f"- `{p}`" for p in copied)
        )
    return "⚠️ No files were copied. Check the output/ directory."


# ── UI ─────────────────────────────────────────────────────────────────────────

INTENTS = [
    (
        "🗡️ Miniatures / Figurines",
        "miniature",
        "0.06mm layers, 0.2mm nozzle, fine detail, tree supports, slow speeds",
    ),
    (
        "⚙️ Functional Parts",
        "functional",
        "0.20mm layers, 3-4 walls, gyroid infill, dimensional accuracy",
    ),
    (
        "🎨 Visual / Display",
        "visual",
        "0.12mm layers, smooth surfaces, aligned seam, ironing",
    ),
    (
        "🚀 Prototype / Draft",
        "prototype",
        "0.24mm layers, fast speeds, minimum quality",
    ),
    (
        "💪 Structural / Load-Bearing",
        "structural",
        "0.20mm layers, 5 walls, 50% cubic infill, max strength",
    ),
    (
        "🧤 Wearable / Flexible (TPU)",
        "wearable",
        "0.20mm layers, slow speeds, minimal retraction",
    ),
]

FILAMENTS = ["PLA", "PETG", "ABS", "ASA", "TPU", "SILK"]

CSS = """
.step-header { font-size: 1.3em; font-weight: bold; margin-bottom: 0.5em; color: #4a9eff; }
.step-sub { color: #888; margin-bottom: 1.2em; font-size: 0.95em; }
.intent-card { border: 1px solid #333; border-radius: 8px; padding: 12px; margin: 4px 0; }
footer { display: none !important; }
"""


def build_ui():
    with gr.Blocks(
        title="OrcaSlicer Printer Wizard", css=CSS, theme=gr.themes.Soft()
    ) as app:
        # ── Shared state ──────────────────────────────────────────────────────
        moonraker_ok = gr.State(False)
        klipper_data = gr.State({})
        ctx_state = gr.State({})
        results_state = gr.State([])
        _gen_preview_state = gr.State("")  # bridges Step 3 output → Step 4 markdown

        gr.Markdown("# 🖨️ OrcaSlicer Printer Setup Wizard")
        gr.Markdown(
            "Set up a custom Klipper printer in OrcaSlicer in 4 steps — no config editing required."
        )

        with gr.Tabs() as tabs:
            # ── Step 1: Connect ───────────────────────────────────────────────
            with gr.Tab("1 · Connect", id="tab_connect"):
                gr.Markdown(
                    '<div class="step-header">Step 1 — Connect to your printer</div>'
                )
                gr.Markdown(
                    '<div class="step-sub">Enter your Moonraker URL. If you don\'t have Klipper, skip this step and enter printer specs manually.</div>'
                )

                moonraker_url = gr.Textbox(
                    label="Moonraker URL",
                    placeholder="http://192.168.1.100:7125",
                    info="The IP address of your Klipper printer's Moonraker API",
                )
                with gr.Row():
                    test_btn = gr.Button("🔌 Test Connection", variant="secondary")
                    skip_btn = gr.Button("Skip (manual entry)", variant="secondary")

                connect_status = gr.Markdown("")
                connect_next = gr.Button("Next →", variant="primary", visible=False)

                def on_test(url):
                    msg, valid_url = test_moonraker(url)
                    if valid_url:
                        kdata = fetch_klipper_config(valid_url)
                        summary = ""
                        if kdata:
                            summary = (
                                f"\n\n**Detected from Klipper config:**\n"
                                f"- Max velocity: {kdata.get('max_velocity')} mm/s\n"
                                f"- Max accel: {kdata.get('max_accel')} mm/s²\n"
                                f"- Nozzle: {kdata.get('nozzle_diameter')} mm\n"
                                f"- Pressure advance: {kdata.get('pressure_advance')}"
                            )
                        return msg + summary, True, kdata, gr.update(visible=True)
                    return msg, False, {}, gr.update(visible=False)

                def on_skip():
                    return (
                        "⏭️ Skipped — enter specs manually in the next step.",
                        True,
                        {},
                        gr.update(visible=True),
                    )

                test_btn.click(
                    on_test,
                    inputs=[moonraker_url],
                    outputs=[connect_status, moonraker_ok, klipper_data, connect_next],
                )
                skip_btn.click(
                    on_skip,
                    outputs=[connect_status, moonraker_ok, klipper_data, connect_next],
                )
                connect_next.click(
                    lambda: gr.update(selected="tab_hardware"), outputs=[tabs]
                )

            # ── Step 2: Hardware ──────────────────────────────────────────────
            with gr.Tab("2 · Hardware", id="tab_hardware"):
                gr.Markdown(
                    '<div class="step-header">Step 2 — Tell us about your printer</div>'
                )
                gr.Markdown(
                    '<div class="step-sub">These details determine speed limits, acceleration caps, and profile defaults.</div>'
                )

                with gr.Row():
                    printer_name = gr.Textbox(
                        label="Printer name",
                        placeholder="My Ender 3 Pro",
                        info="Used as the profile name in OrcaSlicer",
                    )
                    kinematics = gr.Dropdown(
                        label="Motion system",
                        choices=[
                            "Cartesian (bed-slinger)",
                            "CoreXY",
                            "CoreXZ",
                            "Delta",
                        ],
                        value="Cartesian (bed-slinger)",
                    )

                with gr.Row():
                    build_x = gr.Number(label="Build volume X (mm)", value=235)
                    build_y = gr.Number(label="Build volume Y (mm)", value=235)
                    build_z = gr.Number(label="Build volume Z (mm)", value=250)

                with gr.Row():
                    nozzle_diameter = gr.Dropdown(
                        label="Nozzle diameter",
                        choices=["0.2mm", "0.4mm", "0.6mm", "0.8mm"],
                        value="0.4mm",
                        info="0.2mm recommended for miniatures",
                    )
                    extruder_type = gr.Dropdown(
                        label="Extruder type",
                        choices=["Direct Drive", "Bowden"],
                        value="Direct Drive",
                    )

                with gr.Row():
                    hotend_model = gr.Dropdown(
                        label="Hotend model",
                        choices=[
                            "Stock PTFE (Creality/Ender)",
                            "All-Metal (Creality/Ender)",
                            "E3D V6",
                            "Dragon / Rapido / Dragonfly",
                            "Volcano / High-Flow",
                            "Bambu stock",
                            "Other",
                        ],
                        value="Stock PTFE (Creality/Ender)",
                        info="Determines max volumetric flow rate",
                    )
                    cooling = gr.Dropdown(
                        label="Part cooling",
                        choices=[
                            "Single 4010 fan",
                            "Single 5015 fan",
                            "Dual 5015 fans",
                            "4020 blower",
                            "Stock",
                        ],
                        value="Stock",
                    )

                enclosure = gr.Radio(
                    label="Enclosure?",
                    choices=["No", "Yes"],
                    value="No",
                    info="Required for ABS/ASA. Affects material recommendations.",
                )

                hw_note = gr.Markdown("", visible=False)

                with gr.Row():
                    hw_back = gr.Button("← Back")
                    hw_next = gr.Button("Next →", variant="primary")

                def on_hw_next(
                    url, kdata, name, kin, bx, by, bz, nozzle, ext, hotend, cool, enc
                ):
                    # Warn if 0.2mm nozzle not selected for miniatures
                    note = ""
                    if nozzle != "0.2mm":
                        note = "💡 **Tip:** For miniatures, a 0.2mm nozzle gives significantly better detail."
                    return gr.update(value=note, visible=bool(note)), gr.update(
                        selected="tab_intent"
                    )

                hw_back.click(lambda: gr.update(selected="tab_connect"), outputs=[tabs])
                hw_next.click(
                    on_hw_next,
                    inputs=[
                        moonraker_url,
                        klipper_data,
                        printer_name,
                        kinematics,
                        build_x,
                        build_y,
                        build_z,
                        nozzle_diameter,
                        extruder_type,
                        hotend_model,
                        cooling,
                        enclosure,
                    ],
                    outputs=[hw_note, tabs],
                )

            # ── Step 3: Intent ────────────────────────────────────────────────
            with gr.Tab("3 · Print Intent", id="tab_intent"):
                gr.Markdown(
                    '<div class="step-header">Step 3 — What will you print?</div>'
                )
                gr.Markdown(
                    '<div class="step-sub">Select one or more print intents. A separate optimized process profile will be generated for each.</div>'
                )

                intent_choices = gr.CheckboxGroup(
                    label="Print intents",
                    choices=[f"{label}  —  {desc}" for label, _, desc in INTENTS],
                    value=[
                        "⚙️ Functional Parts  —  0.20mm layers, 3-4 walls, gyroid infill, dimensional accuracy"
                    ],
                    info="You can select multiple — one profile per intent will be generated",
                )

                filament_choice = gr.Dropdown(
                    label="Primary filament",
                    choices=FILAMENTS,
                    value="PLA",
                    info="A filament profile with sensible defaults will be generated. Calibrate temps/PA/flow afterward.",
                )

                filament_note = gr.Markdown(
                    "ℹ️ **Calibration reminder:** The generated filament profile uses safe defaults. "
                    "Run Temperature → Flow → Pressure Advance calibrations in OrcaSlicer before trusting it for real prints."
                )

                with gr.Row():
                    intent_back = gr.Button("← Back")
                    intent_next = gr.Button("Generate Profiles →", variant="primary")

                intent_back.click(
                    lambda: gr.update(selected="tab_hardware"), outputs=[tabs]
                )

                def on_generate(
                    url,
                    kdata,
                    name,
                    kin,
                    bx,
                    by,
                    bz,
                    nozzle,
                    ext,
                    hotend,
                    cool,
                    enc,
                    intent_labels,
                    filament,
                ):
                    # Map display labels back to intent keys
                    label_to_key = {
                        f"{label}  —  {desc}": key for label, key, desc in INTENTS
                    }
                    selected_intents = [
                        label_to_key[l] for l in intent_labels if l in label_to_key
                    ]

                    if not selected_intents:
                        return (
                            {},
                            [],
                            "⚠️ Select at least one print intent.",
                            gr.update(selected="tab_intent"),
                        )

                    ctx = build_context(
                        url,
                        name,
                        kin,
                        bx,
                        by,
                        bz,
                        nozzle,
                        ext,
                        hotend,
                        cool,
                        enc,
                        kdata,
                    )
                    results = generate_profiles(ctx, selected_intents, filament)

                    # Build preview
                    preview_lines = []
                    for r in results:
                        if "error" in r:
                            preview_lines.append(
                                f"❌ **{r.get('intent', '?')}**: {r['error']}"
                            )
                        else:
                            preview_lines.append(
                                f"✅ **{r['type']}** — `{r['name']}`\n   → `{r['path']}`"
                            )

                    preview = "\n\n".join(preview_lines)
                    return ctx, results, preview, gr.update(selected="tab_output")

                intent_next.click(
                    on_generate,
                    inputs=[
                        moonraker_url,
                        klipper_data,
                        printer_name,
                        kinematics,
                        build_x,
                        build_y,
                        build_z,
                        nozzle_diameter,
                        extruder_type,
                        hotend_model,
                        cooling,
                        enclosure,
                        intent_choices,
                        filament_choice,
                    ],
                    outputs=[ctx_state, results_state, _gen_preview_state, tabs],
                )

            # ── Step 4: Output ────────────────────────────────────────────────
            with gr.Tab("4 · Done", id="tab_output"):
                gr.Markdown(
                    '<div class="step-header">Step 4 — Profiles generated</div>'
                )

                gen_preview = gr.Markdown(
                    "*Generate profiles in Step 3 to see results here.*"
                )
                copy_status = gr.Markdown("")

                # Sync the state into the visible markdown
                _gen_preview_state.change(
                    lambda v: v, inputs=[_gen_preview_state], outputs=[gen_preview]
                )

                orca_dir = gr.Textbox(
                    label="OrcaSlicer profile directory",
                    value=detect_orcaslicer_profile_dir() or "",
                    info="Auto-detected. Edit if wrong.",
                    interactive=True,
                )

                with gr.Row():
                    copy_btn = gr.Button("📂 Copy to OrcaSlicer", variant="primary")
                    restart_btn = gr.Button("🔄 Start Over", variant="secondary")

                gr.Markdown(
                    "**After copying:** Restart OrcaSlicer. Your new printer and process profiles "
                    "will appear in the printer/process dropdowns.\n\n"
                    "**Next steps:**\n"
                    "1. Select your new printer in OrcaSlicer\n"
                    "2. Run filament calibrations (Temperature → Flow → Pressure Advance)\n"
                    "3. For miniatures: verify 0.2mm nozzle is installed\n"
                    "4. Print a test model before committing to long prints"
                )

                def on_copy(results, orca_dir_val):
                    return copy_to_orcaslicer(results, orca_dir_val)

                def on_restart():
                    return gr.update(selected="tab_connect")

                copy_btn.click(
                    on_copy, inputs=[results_state, orca_dir], outputs=[copy_status]
                )
                restart_btn.click(on_restart, outputs=[tabs])

    return app


if __name__ == "__main__":
    print("Starting OrcaSlicer Printer Setup Wizard...")
    print(f"Repo root: {REPO_ROOT}")
    print(f"OrcaSlicer profile dir: {detect_orcaslicer_profile_dir() or 'not found'}")
    app = build_ui()
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        show_error=True,
    )
