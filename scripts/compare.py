#!/usr/bin/env python3
"""Compatibility wrapper around aipreflight.compare."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aipreflight.compare import main  # noqa: E402

if __name__ == "__main__":
    main()
