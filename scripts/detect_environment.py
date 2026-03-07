import json
import os
import platform
import sys
from pathlib import Path

def detect_environment():
    system = platform.system().lower()
    home = Path.home()
    
    env = {
        "os": system,
        "orcaslicer_found": False,
        "orcaslicer_path": "",
        "orcaslicer_version": "",
        "orcaslicer_profile_dir": "",
        "orcaslicer_profile_dir_exists": False
    }

    if system == "darwin":  # macOS
        candidates = [
            Path("/Applications/OrcaSlicer.app"),
            home / "Applications/OrcaSlicer.app"
        ]
        for c in candidates:
            if c.exists():
                env["orcaslicer_path"] = str(c)
                env["orcaslicer_found"] = True
                break
        env["orcaslicer_profile_dir"] = str(home / "Library/Application Support/OrcaSlicer/user/default")

    elif system == "windows":
        appdata = os.environ.get("APPDATA")
        local_appdata = os.environ.get("LOCALAPPDATA")
        program_files = os.environ.get("ProgramFiles")
        
        candidates = []
        if program_files:
            candidates.append(Path(program_files) / "OrcaSlicer" / "orca-slicer.exe")
        if local_appdata:
            candidates.append(Path(local_appdata) / "OrcaSlicer" / "orca-slicer.exe")
        
        for c in candidates:
            if c.exists():
                env["orcaslicer_path"] = str(c)
                env["orcaslicer_found"] = True
                break
        
        if appdata:
            env["orcaslicer_profile_dir"] = str(Path(appdata) / "OrcaSlicer" / "user" / "default")

    else:  # Linux
        candidates = [
            Path("/usr/bin/orca-slicer"),
            Path("/usr/local/bin/orca-slicer"),
            home / ".local/bin/orca-slicer"
        ]
        # Check for AppImage
        appimages = list(home.glob("**/OrcaSlicer*.AppImage"))
        candidates.extend(appimages)

        for c in candidates:
            if c.exists():
                env["orcaslicer_path"] = str(c)
                env["orcaslicer_found"] = True
                break
        
        env["orcaslicer_profile_dir"] = str(home / ".config" / "OrcaSlicer" / "user" / "default")

    if env["orcaslicer_profile_dir"]:
        env["orcaslicer_profile_dir_exists"] = Path(env["orcaslicer_profile_dir"]).exists()

    print(json.dumps(env, indent=2))

if __name__ == "__main__":
    detect_environment()
