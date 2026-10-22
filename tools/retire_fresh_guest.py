#!/usr/bin/env python3
"""Compatibility command for the shared PRoot guest retirement service."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import proot_guest_retirement as _core

if __name__ == "__main__":
    raise SystemExit(_core.main())

sys.modules[__name__] = _core
