"""Process-isolated adapter for the stl2step CLI.

This module deliberately has no Fusion imports so its contract can be checked
with ordinary Python outside Fusion.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


class EngineError(RuntimeError):
    """The converter could not be located or did not produce a usable result."""


CONVERSION_TIMEOUT_SECONDS = 3600


def _bundled_relative_path() -> Path | None:
    machine = platform.machine().lower()

    if os.name == "nt":
        return Path("bin") / "windows-x86_64" / "stl2step.exe"
    if platform.system() == "Darwin":
        architecture = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
        return Path("bin") / f"macos-{architecture}" / "stl2step"
    return None


def resolve_executable(addin_directory: Path) -> Path:
    configured = os.environ.get("STL2STEP_EXECUTABLE")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return candidate.resolve()
        raise EngineError(
            f"STL2STEP_EXECUTABLE points to a missing file: {candidate}"
        )

    bundled = _bundled_relative_path()
    if bundled:
        candidate = addin_directory / bundled
        if candidate.is_file():
            return candidate.resolve()

    discovered = shutil.which("stl2step")
    if discovered:
        return Path(discovered).resolve()

    expected = addin_directory / (bundled or Path("bin") / "stl2step")
    raise EngineError(
        "Could not find stl2step. Set STL2STEP_EXECUTABLE, put it on PATH, "
        f"or install the platform binary at {expected}."
    )


def parse_result(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        if line.startswith("RESULT "):
            try:
                result = json.loads(line[len("RESULT ") :])
            except json.JSONDecodeError as exc:
                raise EngineError(f"Invalid RESULT JSON: {exc}") from exc
            if not isinstance(result, dict):
                raise EngineError("RESULT payload was not a JSON object")
            return result
    raise EngineError("stl2step did not emit a RESULT line")


def convert(
    executable: Path,
    input_stl: Path,
    output_step: Path,
    *,
    units: str,
    mode: str = "trueform",
) -> dict[str, Any]:
    if units not in {"mm", "in"}:
        raise ValueError(f"unsupported STL units: {units}")
    if mode not in {"trueform", "verbatim"}:
        raise ValueError(f"unsupported conversion mode: {mode}")

    command = [
        str(executable),
        str(input_stl),
        "-o",
        str(output_step),
        "--quiet",
        "--no-verify",
        "--engine",
        mode,
        "--units",
        units,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=CONVERSION_TIMEOUT_SECONDS,
        # Fusion is a GUI process. Without this flag, Windows opens a blank
        # console window for the console-subsystem converter and makes a
        # completed conversion look like a hung add-in.
        creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0)
                       if os.name == "nt" else 0),
    )

    try:
        result = parse_result(completed.stdout)
    except EngineError as exc:
        detail = completed.stderr.strip() or str(exc)
        raise EngineError(
            f"stl2step exited {completed.returncode}: {detail}"
        ) from exc

    if completed.returncode not in {0, 2} or not result.get("ok"):
        detail = result.get("error") or completed.stderr.strip() or "conversion failed"
        raise EngineError(f"stl2step exited {completed.returncode}: {detail}")
    if not output_step.is_file():
        raise EngineError("stl2step reported success but the STEP file is missing")

    return result
