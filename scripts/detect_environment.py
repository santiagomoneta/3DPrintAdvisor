"""
detect_environment.py — Detect OrcaSlicer installation and profile directory.

Key behaviour: when the user is logged in to OrcaSlicer, profiles live under
  user/<account_id>/   (e.g. user/2064502572/)
NOT under
  user/default/

This script scans the user/ directory for numeric subdirectories (account IDs)
and prefers them over the "default" fallback.  The detected account_id is
returned in the output so other scripts can write .info files with the correct
user_id field.
"""

import json
import os
import platform
import re
from pathlib import Path


def _find_account_profile_dir(user_dir: Path):
    """
    Scan <user_dir> for a logged-in account subdirectory.

    OrcaSlicer creates user/<numeric_account_id>/ when the user signs in.
    Returns (profile_dir, account_id) for the most-recently-modified numeric
    subdirectory, or (default_dir, "") if only "default" exists.
    """
    if not user_dir.exists():
        return str(user_dir / "default"), ""

    # Collect all subdirectories whose name is purely numeric (account IDs).
    numeric_dirs = [
        d for d in user_dir.iterdir() if d.is_dir() and re.fullmatch(r"\d+", d.name)
    ]

    if numeric_dirs:
        # Pick the most recently modified one (in case of multiple accounts).
        best = max(numeric_dirs, key=lambda d: d.stat().st_mtime)
        return str(best), best.name

    return str(user_dir / "default"), ""


def detect_environment():
    system = platform.system().lower()
    home = Path.home()

    env = {
        "os": system,
        "orcaslicer_found": False,
        "orcaslicer_path": "",
        "orcaslicer_version": "",
        "orcaslicer_profile_dir": "",
        "orcaslicer_profile_dir_exists": False,
        # Populated when a logged-in account directory is found.
        # Empty string means the user is not logged in (using "default").
        "orcaslicer_account_id": "",
    }

    if system == "darwin":  # macOS
        candidates = [
            Path("/Applications/OrcaSlicer.app"),
            home / "Applications/OrcaSlicer.app",
        ]
        for c in candidates:
            if c.exists():
                env["orcaslicer_path"] = str(c)
                env["orcaslicer_found"] = True
                break

        user_dir = home / "Library" / "Application Support" / "OrcaSlicer" / "user"
        profile_dir, account_id = _find_account_profile_dir(user_dir)
        env["orcaslicer_profile_dir"] = profile_dir
        env["orcaslicer_account_id"] = account_id

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
            user_dir = Path(appdata) / "OrcaSlicer" / "user"
            profile_dir, account_id = _find_account_profile_dir(user_dir)
            env["orcaslicer_profile_dir"] = profile_dir
            env["orcaslicer_account_id"] = account_id

    else:  # Linux
        candidates = [
            Path("/usr/bin/orca-slicer"),
            Path("/usr/local/bin/orca-slicer"),
            home / ".local/bin/orca-slicer",
        ]
        # Check for AppImage in home directory tree.
        appimages = list(home.glob("OrcaSlicer*.AppImage"))
        candidates.extend(appimages)

        for c in candidates:
            if c.exists():
                env["orcaslicer_path"] = str(c)
                env["orcaslicer_found"] = True
                break

        user_dir = home / ".config" / "OrcaSlicer" / "user"
        profile_dir, account_id = _find_account_profile_dir(user_dir)
        env["orcaslicer_profile_dir"] = profile_dir
        env["orcaslicer_account_id"] = account_id

    if env["orcaslicer_profile_dir"]:
        env["orcaslicer_profile_dir_exists"] = Path(
            env["orcaslicer_profile_dir"]
        ).exists()

    print(json.dumps(env, indent=2))


if __name__ == "__main__":
    detect_environment()
