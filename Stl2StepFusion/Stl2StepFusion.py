"""Fusion add-in prototype for stl2step.

The converter runs in a worker thread. Fusion API calls remain on the main
thread and the generated STEP is imported from a custom-event handler after the
toolbar command has ended.
"""

from __future__ import annotations

import json
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

_app = None
_ui = None
_completed_event = None
_command_definition = None
_handlers = []
_workers = set()
_conversion_in_progress = False
_progress_dialog = None


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


def _result_summary(result: dict) -> str:
    lines = [
        "The STEP geometry was imported.",
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
            if not payload.get("ok"):
                _show_error(
                    "Conversion failed.\n\n"
                    + payload.get("error", "The converter did not produce a STEP file.")
                )
                return

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
            _conversion_in_progress = False
            if not preserve_temp_directory:
                _remove_temp_directory(payload)


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
        )
        payload["result"]["mode"] = "TrueForm" if mode == "trueform" else "Verbatim"
        payload["ok"] = True
    except Exception as exc:
        payload["error"] = str(exc)
    finally:
        try:
            _app.fireCustomEvent(COMPLETED_EVENT_ID, json.dumps(payload))
        finally:
            _conversion_in_progress = False
        _workers.discard(current_thread)


class ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, _args):
        global _conversion_in_progress
        try:
            if _conversion_in_progress:
                _show_error("A conversion is already in progress. Please wait for it to finish.")
                return

            design = adsk.fusion.Design.cast(_app.activeProduct)
            if not design:
                _show_error("Open or create a Fusion Design before running this command.")
                return

            file_dialog = _ui.createFileDialog()
            file_dialog.title = "Choose an STL — result opens as a new Fusion document"
            file_dialog.filter = "STL mesh (*.stl)"
            if file_dialog.showOpen() != adsk.core.DialogResults.DialogOK:
                return

            buttons = adsk.core.MessageBoxButtonTypes.YesNoCancelButtonType
            choice = _ui.messageBox(
                "The converted STEP will open in a NEW Fusion document.\n"
                "Your currently open document will not be modified.\n\n"
                "Does this STL use millimetres?\n\n"
                "Yes = millimetres\nNo = inches\nCancel = stop",
                COMMAND_NAME,
                buttons,
            )
            if choice == adsk.core.DialogResults.DialogCancel:
                return
            units = "mm" if choice == adsk.core.DialogResults.DialogYes else "in"

            mode_choice = _ui.messageBox(
                "How should this STL be converted?\n\n"
                "Recommended — TrueForm\n"
                "Recovers editable planes, cylinders, and fillets.\n\n"
                "Verbatim\n"
                "Preserves the original STL facets and is usually faster.\n\n"
                "Yes = TrueForm (Recommended)\n"
                "No = Verbatim\n"
                "Cancel = stop",
                COMMAND_NAME,
                buttons,
            )
            if mode_choice == adsk.core.DialogResults.DialogCancel:
                return
            mode = "trueform" if mode_choice == adsk.core.DialogResults.DialogYes else "verbatim"

            _conversion_in_progress = True
            global _progress_dialog
            _progress_dialog = _ui.createProgressDialog()
            _progress_dialog.cancelButtonText = "Run in background"
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
            _show_error(_short_error("Could not start conversion", exc))


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
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
    global _completed_event, _command_definition
    try:
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
