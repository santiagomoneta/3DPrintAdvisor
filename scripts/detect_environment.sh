#!/usr/bin/env bash
# detect_environment.sh — Detect OS, find OrcaSlicer install + profile directory
# Usage: bash detect_environment.sh
# Output: JSON to stdout

set -euo pipefail

detect_os() {
  case "$(uname -s)" in
    Darwin)  echo "darwin" ;;
    Linux)
      if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "windows_wsl"
      else
        echo "linux"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

find_orcaslicer() {
  local os="$1"
  local path=""
  local version=""
  local profile_dir=""

  case "$os" in
    darwin)
      # Check standard macOS locations
      for candidate in \
        "/Applications/OrcaSlicer.app" \
        "$HOME/Applications/OrcaSlicer.app" \
        "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer"; do
        if [ -e "$candidate" ]; then
          path="$candidate"
          break
        fi
      done
      # Also try `which` / `mdfind`
      if [ -z "$path" ]; then
        path=$(mdfind "kMDItemFSName == 'OrcaSlicer.app'" 2>/dev/null | head -1) || true
      fi
      # Profile directory on macOS
      profile_dir="$HOME/Library/Application Support/OrcaSlicer/user/default"
      # Try to get version from Info.plist
      if [ -n "$path" ] && [ -f "${path}/Contents/Info.plist" ]; then
        version=$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "${path}/Contents/Info.plist" 2>/dev/null) || true
      fi
      ;;

    linux)
      # Check common Linux locations
      for candidate in \
        "/usr/bin/orca-slicer" \
        "/usr/local/bin/orca-slicer" \
        "$HOME/OrcaSlicer/orca-slicer" \
        "$HOME/.local/bin/orca-slicer"; do
        if [ -x "$candidate" ]; then
          path="$candidate"
          break
        fi
      done
      # Flatpak
      if [ -z "$path" ] && command -v flatpak &>/dev/null; then
        if flatpak list 2>/dev/null | grep -qi orcaslicer; then
          path="flatpak:com.bambulab.OrcaSlicer"
        fi
      fi
      # AppImage in common locations
      if [ -z "$path" ]; then
        path=$(find "$HOME" /opt /usr/local -maxdepth 3 -name "OrcaSlicer*.AppImage" -type f 2>/dev/null | head -1) || true
      fi
      # Also try which
      if [ -z "$path" ]; then
        path=$(which orca-slicer 2>/dev/null) || true
      fi
      # Profile directory on Linux
      profile_dir="$HOME/.config/OrcaSlicer/user/default"
      # Version from binary
      if [ -n "$path" ] && [ -x "$path" ] && [[ "$path" != flatpak:* ]]; then
        version=$("$path" --version 2>/dev/null | grep -oP '[\d]+\.[\d]+\.[\d]+' | head -1) || true
      fi
      ;;

    windows_wsl)
      # Running in WSL — look for OrcaSlicer on the Windows side
      local win_appdata=""
      # Try to resolve Windows %APPDATA%
      if command -v wslpath &>/dev/null; then
        win_appdata=$(wslpath "$(cmd.exe /C 'echo %APPDATA%' 2>/dev/null | tr -d '\r')" 2>/dev/null) || true
      fi
      if [ -z "$win_appdata" ]; then
        # Fallback: common default
        local win_user
        win_user=$(cmd.exe /C 'echo %USERNAME%' 2>/dev/null | tr -d '\r') || true
        if [ -n "$win_user" ]; then
          win_appdata="/mnt/c/Users/${win_user}/AppData/Roaming"
        fi
      fi

      # Search for OrcaSlicer executable on Windows side
      for candidate in \
        "/mnt/c/Program Files/OrcaSlicer/orca-slicer.exe" \
        "/mnt/c/Program Files (x86)/OrcaSlicer/orca-slicer.exe" \
        "/mnt/c/Users/*/AppData/Local/OrcaSlicer/orca-slicer.exe"; do
        # Handle glob
        for match in $candidate; do
          if [ -f "$match" ]; then
            path="$match"
            break 2
          fi
        done
      done

      # Profile directory (Windows AppData via WSL path)
      if [ -n "$win_appdata" ]; then
        profile_dir="${win_appdata}/OrcaSlicer/user/default"
      fi
      ;;

    windows)
      # Native Windows (Git Bash / MSYS2)
      for candidate in \
        "/c/Program Files/OrcaSlicer/orca-slicer.exe" \
        "$APPDATA/Local/OrcaSlicer/orca-slicer.exe" \
        "$LOCALAPPDATA/OrcaSlicer/orca-slicer.exe"; do
        if [ -f "$candidate" ]; then
          path="$candidate"
          break
        fi
      done
      profile_dir="$APPDATA/OrcaSlicer/user/default"
      ;;
  esac

  # Check if profile directory actually exists
  local profile_exists="false"
  if [ -n "$profile_dir" ] && [ -d "$profile_dir" ]; then
    profile_exists="true"
  fi

  # Emit JSON
  cat <<ENDJSON
{
  "os": "$os",
  "orcaslicer_found": $([ -n "$path" ] && echo "true" || echo "false"),
  "orcaslicer_path": "$path",
  "orcaslicer_version": "$version",
  "orcaslicer_profile_dir": "$profile_dir",
  "orcaslicer_profile_dir_exists": $profile_exists
}
ENDJSON
}

# Main
os=$(detect_os)
find_orcaslicer "$os"
