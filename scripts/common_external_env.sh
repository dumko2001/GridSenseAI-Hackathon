#!/bin/zsh
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
RUNTIME_ROOT="${GRIDSENSE_RUNTIME_ROOT:-$ROOT_DIR/.runtime}"
HOME_DIR="$RUNTIME_ROOT/home"
CACHE_DIR="$RUNTIME_ROOT/cache"
TMP_DIR="$RUNTIME_ROOT/tmp"

mkdir -p \
  "$HOME_DIR" \
  "$CACHE_DIR/huggingface/hub" \
  "$CACHE_DIR/huggingface/transformers" \
  "$CACHE_DIR/huggingface/datasets" \
  "$CACHE_DIR/torch" \
  "$CACHE_DIR/matplotlib" \
  "$CACHE_DIR/pip" \
  "$CACHE_DIR/pycache" \
  "$CACHE_DIR/openmeteo" \
  "$TMP_DIR" \
  "$ROOT_DIR/.streamlit"

export GRIDSENSE_RUNTIME_ROOT="$RUNTIME_ROOT"
export HOME="$HOME_DIR"
export XDG_CACHE_HOME="$CACHE_DIR"
export TMPDIR="$TMP_DIR"
export HF_HOME="$CACHE_DIR/huggingface"
export HUGGINGFACE_HUB_CACHE="$HF_HOME/hub"
export TRANSFORMERS_CACHE="$HF_HOME/transformers"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TORCH_HOME="$CACHE_DIR/torch"
export MPLCONFIGDIR="$CACHE_DIR/matplotlib"
export PIP_CACHE_DIR="$CACHE_DIR/pip"
export PYTHONPYCACHEPREFIX="$CACHE_DIR/pycache"
export STREAMLIT_CONFIG_DIR="$ROOT_DIR/.streamlit"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export HF_HUB_DISABLE_TELEMETRY=1
export PYTHONNOUSERSITE=1
