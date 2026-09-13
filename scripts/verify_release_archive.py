"""Validate the contents of a packaged Fusion add-on archive."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


def verify_archive(archive: Path, addon_dir: str = "Stl2StepFusion") -> None:
    prefix = addon_dir.rstrip("/") + "/"
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        required = {
            "LICENSE",
            "LICENSE.stl2step",
            "README.md",
            "THIRD_PARTY_NOTICES.md",
            "config/engine-release.json",
            f"{prefix}package.xml",
            f"{prefix}bin/windows-x86_64/stl2step.exe",
        }
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"archive is missing required files: {', '.join(missing)}")
        dlls = [name for name in names if name.startswith(f"{prefix}bin/windows-x86_64/") and name.lower().endswith(".dll")]
        if not dlls:
            raise ValueError("archive contains no engine runtime DLLs")
        if any("cdracars/stl2step" in name.lower() or "engine-pin.json" in name.lower() for name in names):
            raise ValueError("archive contains a stale fork or legacy engine pin reference")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--addon-dir", default="Stl2StepFusion")
    args = parser.parse_args()
    verify_archive(args.archive, args.addon_dir)
    print(f"Validated release archive: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

