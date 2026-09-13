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
import threading
import time
from pathlib import Path
from typing import Any


class EngineError(RuntimeError):
    """The converter could not be located or did not produce a usable result."""


class EngineCancelled(EngineError):
    """The converter was stopped at the user's request."""


CONVERSION_TIMEOUT_SECONDS = 3600
VERSION_TIMEOUT_SECONDS = 10


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


def version(executable: Path) -> str:
    """Return the version reported by the engine executable."""
    completed = subprocess.run(
        [str(executable), "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=VERSION_TIMEOUT_SECONDS,
        creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0)
                       if os.name == "nt" else 0),
    )
    reported = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0 or not reported:
        raise EngineError(
            f"stl2step version check failed with exit code {completed.returncode}"
        )
    return reported.splitlines()[0]


def _run_conversion_process(
    command: list[str],
    *,
    cancel_event=None,
) -> subprocess.CompletedProcess[str]:
    """Run the CLI while allowing the host to terminate it safely."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0)
                       if os.name == "nt" else 0),
    )
    deadline = time.monotonic() + CONVERSION_TIMEOUT_SECONDS
    communication = {}
    communication_done = threading.Event()

    def collect_output():
        try:
            communication["result"] = process.communicate()
        except BaseException as exc:  # pragma: no cover - defensive worker cleanup
            communication["error"] = exc
        finally:
            communication_done.set()

    # Drain both pipes while the process runs. Waiting until the end can fill a
    # native pipe buffer and make the converter appear to hang.
    collector = threading.Thread(target=collect_output, name="stl2step-output", daemon=True)
    collector.start()
    try:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                communication_done.wait(5)
                raise EngineCancelled("Conversion cancelled")
            if time.monotonic() >= deadline:
                process.kill()
                process.wait(timeout=5)
                communication_done.wait(5)
                raise EngineError(
                    f"stl2step conversion exceeded {CONVERSION_TIMEOUT_SECONDS} seconds"
                )
            if communication_done.wait(0.1):
                break
        if "error" in communication:
            raise communication["error"]
        stdout, stderr = communication["result"]
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except Exception:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        communication_done.wait(5)
        raise


def convert(
    executable: Path,
    input_stl: Path,
    output_step: Path,
    *,
    units: str,
    mode: str = "trueform",
    cancel_event=None,
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
    completed = _run_conversion_process(command, cancel_event=cancel_event)

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
