#!/usr/bin/env python3
"""Compatibility wrapper. Prefer `aipreflight diagnose runs/latest`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aipreflight.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["diagnose", *sys.argv[1:]]))
