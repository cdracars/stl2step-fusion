"""Fusion add-in prototype for stl2step.

The converter runs in a worker thread. Fusion API calls remain on the main
thread and the generated STEP is imported from a custom-event handler after the
toolbar command has ended.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

import adsk.core
import adsk.fusion

# Fusion's Add-In Manager does not guarantee that the add-in directory is on
# sys.path at startup. Make the sibling engine import deterministic regardless
# of Fusion's current working directory.
_ADDIN_DIRECTORY = Path(__file__).resolve().parent
if str(_ADDIN_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(_ADDIN_DIRECTORY))

import engine


COMMAND_ID = "cdracars_stl2step_fusion_convert"
COMMAND_NAME = "STL to STEP Solid"
COMMAND_DESCRIPTION = (
    "Convert an STL to STEP and open the result in a new Fusion document. "
    "The current document is not modified."
)
PANEL_ID = "SolidScriptsAddinsPanel"
DESIGN_WORKSPACE_ID = "FusionSolidEnvironment"
COMPLETED_EVENT_ID = "cdracars_stl2step_fusion_completed"
UNITS_INPUT_ID = "stl2step_units"
MODE_INPUT_ID = "stl2step_mode"
PREFERENCES_FILENAME = "stl2step-fusion-preferences.json"

_app = None
_ui = None
_completed_event = None
_command_definition = None
_handlers = []
_workers = set()
_conversion_in_progress = False
_progress_dialog = None
_cancel_event = None


class _CancelSignal:
    """Thread-safe cancellation signal with Fusion progress integration."""

    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        self._event.set()

    def is_set(self):
        if self._event.is_set():
            return True
        try:
            return bool(_progress_dialog and _progress_dialog.wasCancelled)
        except RuntimeError:
            return True


def _show_error(message: str) -> None:
    if _ui:
        _ui.messageBox(message, COMMAND_NAME)


def _set_status(message: str) -> None:
    if _ui:
        try:
            _ui.statusMessage = message
        except RuntimeError:
            pass


def _hide_progress() -> None:
    global _progress_dialog
    _set_status("")
    if _progress_dialog:
        try:
            _progress_dialog.hide()
        except RuntimeError:
            pass
        finally:
            _progress_dialog = None


def _friendly_warning(warning: str) -> str:
    if warning.startswith("smooth: analytic rebuild reverted"):
        return (
            "One component could not be safely reconstructed analytically, "
            "so it was kept faceted."
        )
    return warning


def _short_error(prefix: str, exc: Exception) -> str:
    detail = str(exc).strip() or type(exc).__name__
    return f"{prefix}: {detail}"


def _preferences_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return root / "stl2step-fusion" / PREFERENCES_FILENAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "stl2step-fusion" / PREFERENCES_FILENAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "stl2step-fusion" / PREFERENCES_FILENAME


def _load_preferences() -> dict[str, str]:
    try:
        preferences = json.loads(_preferences_path().read_text(encoding="utf-8"))
        if not isinstance(preferences, dict):
            return {}
        valid = {"mm", "in", "trueform", "verbatim"}
        return {key: value for key, value in preferences.items()
                if key in {"units", "mode"} and value in valid}
    except (OSError, ValueError, TypeError):
        return {}


def _save_preferences(units: str, mode: str) -> None:
    try:
        path = _preferences_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"units": units, "mode": mode}, indent=2) + "\n", encoding="utf-8")
    except OSError:
        # Preferences are a convenience and must never prevent conversion.
        pass


def _result_summary(result: dict) -> str:
    lines = [
        "The STEP geometry was imported.",
        f"Source: {result.get('inputName', 'selected STL')}",
        f"Output document: {result.get('outputName', 'new Fusion document')}",
        f"Output STEP: {result.get('stepPath', 'temporary file')}",
        f"Mode: {result.get('mode', 'TrueForm')}",
        "",
        f"Triangles: {result.get('triangles', 0)}",
        f"Solids: {result.get('solids', 0)}",
        f"Open shells: {result.get('openShells', 0)}",
        f"Faces after reconstruction: {result.get('facesAfterSmooth', result.get('facesAfterUnify', 0))}",
        f"Planes recovered: {result.get('smoothPlanes', 0)}",
        f"Cylinders recovered: {result.get('smoothCylinders', 0)}",
        f"Fillets recovered: {result.get('smoothFillets', 0)}",
        f"Elapsed: {result.get('seconds', 0):.2f}s",
        f"Engine: {result.get('engineVersion', 'unknown')}",
    ]
    warnings = result.get("warnings") or []
    if warnings:
        lines.extend(
            ["", "Warnings:", *[f"- {_friendly_warning(warning)}" for warning in warnings]]
        )
    return "\n".join(lines)


def _remove_temp_directory(payload: dict) -> None:
    temp_directory = payload.get("tempDirectory")
    if temp_directory:
        shutil.rmtree(temp_directory, ignore_errors=True)


class ConversionCompletedHandler(adsk.core.CustomEventHandler):
    def notify(self, args):
        global _conversion_in_progress
        payload = {}
        preserve_temp_directory = False
        try:
            payload = json.loads(args.additionalInfo)
            # Close the progress UI before presenting the result. Otherwise
            # Fusion stacks the completion modal over the old progress dialog.
            _hide_progress()
            if payload.get("cancelled"):
                _set_status("STL to STEP: conversion cancelled")
                return
            if not payload.get("ok"):
                _show_error(
                    "Conversion failed.\n\n"
                    + payload.get("error", "The converter did not produce a STEP file.")
                )
                return

            _set_status("STL to STEP: importing generated STEP into a new document…")
            if _ui.activeCommand != "SelectCommand":
                select_command = _ui.commandDefinitions.itemById("SelectCommand")
                if select_command:
                    select_command.execute()

            import_manager = _app.importManager
            options = import_manager.createSTEPImportOptions(payload["stepPath"])
            # Fusion's importToTarget2 is unreliable for unsaved designs and
            # can raise InternalValidationError even for a valid STEP. Open
            # the result as a new document instead; this is deterministic for
            # both saved and unsaved source documents.
            imported_document = import_manager.importToNewDocument(options)
            if imported_document is None:
                raise RuntimeError("Fusion could not open the generated STEP")

            _ui.messageBox(_result_summary(payload["result"]), COMMAND_NAME)
        except Exception as exc:
            if payload.get("ok"):
                preserve_temp_directory = True
                _show_error(
                    "The STEP was created, but Fusion could not import it.\n\n"
                    f"The generated STEP remains at:\n{payload['stepPath']}\n\n"
                    f"{_short_error('Fusion import error', exc)}"
                )
            else:
                _show_error(_short_error("Conversion failed", exc))
        finally:
            _hide_progress()
            if payload.get("ok") and not preserve_temp_directory:
                _set_status("STL to STEP: complete — new document opened")
            if not preserve_temp_directory:
                _remove_temp_directory(payload)
            global _cancel_event
            _cancel_event = None


def _worker(input_path: str, units: str, mode: str) -> None:
    global _conversion_in_progress
    current_thread = threading.current_thread()
    temp_directory = Path(tempfile.mkdtemp(prefix="stl2step-fusion-"))
    output_path = temp_directory / f"{Path(input_path).stem}.step"
    payload = {
        "ok": False,
        "tempDirectory": str(temp_directory),
        "stepPath": str(output_path),
    }

    try:
        executable = engine.resolve_executable(Path(__file__).resolve().parent)
        payload["result"] = engine.convert(
            executable,
            Path(input_path),
            output_path,
            units=units,
            mode=mode,
            cancel_event=_cancel_event,
        )
        try:
            payload["result"]["engineVersion"] = engine.version(executable)
        except Exception:
            # A conversion should remain successful if an older/custom
            # executable does not implement --version.
            payload["result"]["engineVersion"] = "unknown"
        payload["result"]["mode"] = "TrueForm" if mode == "trueform" else "Verbatim"
        payload["result"]["inputName"] = Path(input_path).name
        payload["result"]["outputName"] = output_path.name
        payload["result"]["stepPath"] = str(output_path)
        payload["ok"] = True
    except engine.EngineCancelled as exc:
        payload["cancelled"] = True
        payload["error"] = str(exc)
    except Exception as exc:
        payload["error"] = str(exc)
    try:
        _app.fireCustomEvent(COMPLETED_EVENT_ID, json.dumps(payload))
    except Exception:
        # The completion handler owns the normal state transition. If Fusion
        # is shutting down and the event cannot be queued, avoid leaving the
        # add-in permanently busy.
        _conversion_in_progress = False
        raise
    finally:
        _workers.discard(current_thread)


class ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        global _conversion_in_progress, _cancel_event
        try:
            if _conversion_in_progress:
                _show_error("A conversion is already in progress. Please wait for it to finish.")
                return

            design = adsk.fusion.Design.cast(_app.activeProduct)
            if not design:
                _show_error("Open or create a Fusion Design before running this command.")
                return

            inputs = args.command.commandInputs
            units_input = inputs.itemById(UNITS_INPUT_ID)
            mode_input = inputs.itemById(MODE_INPUT_ID)
            if not units_input or not mode_input:
                raise RuntimeError("Conversion options were not initialized")

            file_dialog = _ui.createFileDialog()
            file_dialog.title = "Choose an STL — result opens as a new Fusion document"
            file_dialog.filter = "STL mesh (*.stl)"
            if file_dialog.showOpen() != adsk.core.DialogResults.DialogOK:
                return

            units = "mm" if units_input.selectedItem.index == 0 else "in"
            mode = "trueform" if mode_input.selectedItem.index == 0 else "verbatim"
            _save_preferences(units, mode)

            _conversion_in_progress = True
            _cancel_event = _CancelSignal()
            global _progress_dialog
            _progress_dialog = _ui.createProgressDialog()
            _progress_dialog.cancelButtonText = "Cancel"
            _progress_dialog.isCancelButtonShown = True
            _progress_dialog.show(
                "STL to STEP",
                f"Conversion in progress: {Path(file_dialog.filename).name}\n\n"
                "Progress percentage is unavailable. Fusion will open the STEP "
                "when conversion finishes.",
                0,
                100,
                0,
            )
            _set_status(
                f"STL to STEP: converting {Path(file_dialog.filename).name}…"
            )
            worker = threading.Thread(
                target=_worker,
                args=(file_dialog.filename, units, mode),
                name="stl2step-fusion-convert",
                daemon=True,
            )
            _workers.add(worker)
            worker.start()
        except Exception as exc:
            _hide_progress()
            _conversion_in_progress = False
            _cancel_event = None
            _show_error(_short_error("Could not start conversion", exc))


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        inputs = args.command.commandInputs
        preferences = _load_preferences()
        units = inputs.addDropDownCommandInput(
            UNITS_INPUT_ID,
            "STL units",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        units.listItems.add(
            "Millimetres (mm)", preferences.get("units", "mm") == "mm",
            "STL has millimetre dimensions",
        )
        units.listItems.add(
            "Inches (in)", preferences.get("units") == "in",
            "STL has inch dimensions",
        )

        mode = inputs.addDropDownCommandInput(
            MODE_INPUT_ID,
            "Conversion mode",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        mode.listItems.add(
            "TrueForm (recommended)",
            preferences.get("mode", "trueform") == "trueform",
            "Recover analytic planes, cylinders, and fillets where possible",
        )
        mode.listItems.add(
            "Verbatim (preserve facets)",
            preferences.get("mode") == "verbatim",
            "Preserve the original faceted STL surfaces",
        )
        args.command.isCancelButtonVisible = True
        args.command.cancelButtonText = "Cancel"
        handler = ExecuteHandler()
        args.command.execute.add(handler)
        _handlers.append(handler)


def run(_context):
    global _app, _ui, _completed_event, _command_definition
    stage = "initialization"
    try:
        stage = "getting Fusion application"
        _app = adsk.core.Application.get()
        if not _app:
            raise RuntimeError("Fusion returned no Application object")

        stage = "getting Fusion user interface"
        _ui = _app.userInterface
        if not _ui:
            raise RuntimeError("Fusion returned no UserInterface object")

        stage = "registering completion event"
        _completed_event = _app.registerCustomEvent(COMPLETED_EVENT_ID)
        if not _completed_event:
            raise RuntimeError(f"Could not register custom event {COMPLETED_EVENT_ID!r}")
        completed_handler = ConversionCompletedHandler()
        _completed_event.add(completed_handler)
        _handlers.append(completed_handler)

        stage = "creating command definition"
        _command_definition = _ui.commandDefinitions.itemById(COMMAND_ID)
        if not _command_definition:
            _command_definition = _ui.commandDefinitions.addButtonDefinition(
                COMMAND_ID,
                COMMAND_NAME,
                COMMAND_DESCRIPTION,
            )
        if not _command_definition:
            raise RuntimeError(f"Could not create command definition {COMMAND_ID!r}")

        stage = "registering command handler"
        created_handler = CommandCreatedHandler()
        _command_definition.commandCreated.add(created_handler)
        _handlers.append(created_handler)

        stage = "locating Design workspace toolbar panel"
        design_workspace = _ui.workspaces.itemById(DESIGN_WORKSPACE_ID)
        panel = design_workspace.toolbarPanels.itemById(PANEL_ID) if design_workspace else None
        if not panel:
            panel = _ui.allToolbarPanels.itemById(PANEL_ID)
        if not panel:
            raise RuntimeError(
                f"Fusion toolbar panel not found: {PANEL_ID} in {DESIGN_WORKSPACE_ID}"
            )

        stage = "adding toolbar command"
        control = panel.controls.itemById(COMMAND_ID)
        if not control:
            control = panel.controls.addCommand(_command_definition)
        if not control:
            raise RuntimeError(f"Could not add {COMMAND_ID!r} to {PANEL_ID}")
        control.isPromoted = True
    except Exception as exc:
        _show_error(_short_error(f"Could not start the add-in during {stage}", exc))


def stop(_context):
    global _completed_event, _command_definition, _conversion_in_progress, _cancel_event
    try:
        # Signal the worker before tearing down Fusion event handlers. The
        # worker will terminate the child process and gracefully handle the
        # completion event becoming unavailable during Fusion shutdown.
        if _cancel_event:
            _cancel_event.cancel()
        _conversion_in_progress = False
        _hide_progress()

        if _ui:
            panel = _ui.allToolbarPanels.itemById(PANEL_ID)
            if panel:
                control = panel.controls.itemById(COMMAND_ID)
                if control:
                    try:
                        control.deleteMe()
                    except RuntimeError as exc:
                        # Fusion can remove the control before invoking stop
                        # (for example when the workspace is closed). Treat
                        # that already-cleaned-up state as success.
                        if "deleted Object" not in str(exc):
                            raise
            if _command_definition:
                try:
                    _command_definition.deleteMe()
                except RuntimeError as exc:
                    if "deleted Object" not in str(exc):
                        raise
                finally:
                    _command_definition = None

        if _completed_event and _app:
            try:
                _app.unregisterCustomEvent(COMPLETED_EVENT_ID)
            except RuntimeError as exc:
                if "deleted Object" not in str(exc):
                    raise
            finally:
                _completed_event = None
        _handlers.clear()
    except Exception as exc:
        _show_error(_short_error("Could not stop the add-in cleanly", exc))
