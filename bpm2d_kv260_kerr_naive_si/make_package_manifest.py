#!/usr/bin/env python3
"""Create or verify the deterministic package SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "SHA256SUMS.txt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_files() -> list[Path]:
    result = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path == MANIFEST:
            continue
        relative = path.relative_to(ROOT)
        if "__pycache__" in relative.parts or "results" in relative.parts:
            continue
        if path.suffix == ".pyc":
            continue
        result.append(path)
    return sorted(result, key=lambda path: path.relative_to(ROOT).as_posix().casefold())


def current_manifest() -> str:
    return "".join(
        f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n"
        for path in package_files()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()

    current = current_manifest()
    if args.write:
        with MANIFEST.open("w", encoding="ascii", newline="\n") as stream:
            stream.write(current)
        print(f"Wrote {len(current.splitlines())} hashes to {MANIFEST.name}.")
        return 0

    expected = MANIFEST.read_text(encoding="ascii")
    if current != expected:
        print("Package manifest mismatch.")
        return 1
    print(f"PASS: {len(current.splitlines())} package hashes match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
