#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
source "$ROOT_DIR/scripts/common_external_env.sh"

VENV_DIR="${VENV_DIR:-$ROOT_DIR/venv-external}"

exec "$VENV_DIR/bin/python" -m streamlit run "$ROOT_DIR/dashboard/app.py" --server.port=8501 --server.address=0.0.0.0
