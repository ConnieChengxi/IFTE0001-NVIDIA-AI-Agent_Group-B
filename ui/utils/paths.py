"""
Path resolution for the UI module.

Adds PROJECT_ROOT and HYBRID_DIR to sys.path so that
imports like `from src.orchestrator import ...` work correctly.
"""

import sys
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent          # .../ui/
PROJECT_ROOT = UI_DIR.parent                              # .../IFTE0001-.../
HYBRID_DIR = PROJECT_ROOT / "hybrid_controller"
OUTPUT_DIR = HYBRID_DIR / "outputs"
TECH_DIR = PROJECT_ROOT / "connie_technical"


def setup_paths():
    """Call once at app startup to make orchestrator imports available."""
    for p in [str(PROJECT_ROOT), str(HYBRID_DIR)]:
        if p not in sys.path:
            sys.path.insert(0, p)
