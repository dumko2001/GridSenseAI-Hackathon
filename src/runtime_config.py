"""
Runtime path configuration for keeping project artifacts on the external drive.
"""
from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path(os.environ.get("GRIDSENSE_RUNTIME_ROOT", PROJECT_ROOT / ".runtime")).resolve()
HOME_DIR = RUNTIME_ROOT / "home"
CACHE_DIR = RUNTIME_ROOT / "cache"
TMP_DIR = RUNTIME_ROOT / "tmp"


def configure_runtime() -> dict[str, str]:
    """Force common ML/tooling caches into the project runtime directory."""
    paths = {
        "GRIDSENSE_RUNTIME_ROOT": str(RUNTIME_ROOT),
        "HOME": str(HOME_DIR),
        "XDG_CACHE_HOME": str(CACHE_DIR),
        "TMPDIR": str(TMP_DIR),
        "HF_HOME": str(CACHE_DIR / "huggingface"),
        "HUGGINGFACE_HUB_CACHE": str(CACHE_DIR / "huggingface" / "hub"),
        "TRANSFORMERS_CACHE": str(CACHE_DIR / "huggingface" / "transformers"),
        "TORCH_HOME": str(CACHE_DIR / "torch"),
        "HF_DATASETS_CACHE": str(CACHE_DIR / "huggingface" / "datasets"),
        "MPLCONFIGDIR": str(CACHE_DIR / "matplotlib"),
        "PIP_CACHE_DIR": str(CACHE_DIR / "pip"),
        "PYTHONPYCACHEPREFIX": str(CACHE_DIR / "pycache"),
        "STREAMLIT_CONFIG_DIR": str(PROJECT_ROOT / ".streamlit"),
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "PYTHONNOUSERSITE": "1",
    }

    for key, value in paths.items():
        os.environ[key] = value

    for directory in {
        RUNTIME_ROOT,
        HOME_DIR,
        CACHE_DIR,
        TMP_DIR,
        Path(paths["HF_HOME"]),
        Path(paths["HUGGINGFACE_HUB_CACHE"]),
        Path(paths["TRANSFORMERS_CACHE"]),
        Path(paths["TORCH_HOME"]),
        Path(paths["HF_DATASETS_CACHE"]),
        Path(paths["MPLCONFIGDIR"]),
        Path(paths["PIP_CACHE_DIR"]),
        Path(paths["PYTHONPYCACHEPREFIX"]),
        Path(paths["STREAMLIT_CONFIG_DIR"]),
    }:
        directory.mkdir(parents=True, exist_ok=True)

    return paths


def describe_runtime() -> str:
    paths = configure_runtime()
    return (
        f"runtime_root={paths['GRIDSENSE_RUNTIME_ROOT']} "
        f"hf_home={paths['HF_HOME']} "
        f"torch_home={paths['TORCH_HOME']} "
        f"tmpdir={paths['TMPDIR']}"
    )


def chdir_project_root() -> str:
    os.chdir(PROJECT_ROOT)
    return str(PROJECT_ROOT)
