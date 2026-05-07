#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/common_external_env.sh"

PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.12}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/venv-external}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing Python interpreter: $PYTHON_BIN"
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$ROOT_DIR/requirements.txt"

echo "External-drive environment ready at $VENV_DIR"
echo "Runtime root: $GRIDSENSE_RUNTIME_ROOT"
