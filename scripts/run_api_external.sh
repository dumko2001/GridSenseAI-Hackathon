#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/common_external_env.sh"

VENV_DIR="${VENV_DIR:-$ROOT_DIR/venv-external}"

exec "$VENV_DIR/bin/python" "$ROOT_DIR/src/api/main.py"
