#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# Reuse installed packages; add only missing OS prerequisites.
needed_packages=()
if ! command -v openscad >/dev/null 2>&1; then
  needed_packages+=(openscad python3-venv)
fi
if [ ! -r /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc ]; then
  needed_packages+=(fonts-noto-cjk)
fi
if [ "${#needed_packages[@]}" -gt 0 ]; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "Install required OS packages using your package manager: ${needed_packages[*]}" >&2
    exit 1
  fi
  if [ "$(id -u)" -eq 0 ]; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${needed_packages[@]}"
  elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo -n apt-get update
    sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${needed_packages[@]}"
  else
    echo "Missing OS packages and no root/passwordless sudo. Ask the environment administrator to install: ${needed_packages[*]}" >&2
    exit 1
  fi
fi
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 12), "Python >=3.12 required (tested with 3.12)"'
if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv || { echo 'venv failed: install the matching python3-venv package.' >&2; exit 1; }
fi
.venv/bin/python -m pip install --no-cache-dir -r requirements.txt
.venv/bin/python -m pip check
mkdir -p input output/stl output/3mf output/preview
openscad --version
.venv/bin/python --version
.venv/bin/python scripts/doctor.py
