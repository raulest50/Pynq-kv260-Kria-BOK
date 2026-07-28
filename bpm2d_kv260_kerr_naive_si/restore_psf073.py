#!/usr/bin/env python3
"""Restore the known-good psf073 overlay after a board benchmark session."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("psf073_root", type=Path)
    return parser.parse_args()


def main() -> int:
    root = parse_args().psf073_root.expanduser().resolve()
    sys.path.insert(0, str(root))
    from bpm2d_driver import BPM2DOverlay

    driver = BPM2DOverlay(root / "bpm2d_kv260_kerr_fast_si.bit")
    print(
        f"Restored {driver.ip_name} at {driver.pl_clock_mhz:.6f} MHz "
        f"in {driver.overlay_load_s:.6f} s."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
