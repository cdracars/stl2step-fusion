# Fusion add-in prototype

This is a Fusion 360 add-in that answers one question:

> Can a user select an STL, convert it outside Fusion, and open the resulting
> STEP B-Rep in a new Fusion document?

The add-in converts an STL selected from disk. It does not modify the currently
open Fusion document or convert an already-imported Fusion mesh body.

## Install for another user (Windows)

1. Copy the complete `Stl2StepFusion` folder to:

   `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`

   The folder must contain `Stl2StepFusion.py`, `Stl2StepFusion.manifest`,
   `engine.py`, and `bin\windows-x86_64\stl2step.exe` with its DLLs.

2. Start or restart Fusion 360.

3. Open **Utilities → Scripts and Add-Ins → Add-Ins**, select
   **Stl2StepFusion**, and verify that **Run on Startup** is checked and **Run**
   is on. If it is not listed, use **+ → My Add-Ins** and select the folder
   containing the manifest (not the `.py` file).

4. In the **UTILITIES** tab, choose **STL to STEP Solid**. Select an STL, choose
   its units, and choose **TrueForm** or **Verbatim**. The result opens as a new
   Fusion document; the current document is not changed.

The packaged Windows folder is self-contained: the OCCT DLLs sit beside the
CLI, so the recipient does not need OpenCASCADE, Python, or a PATH change.

## Install for development

Copy or link the `Stl2StepFusion` directory (the folder containing both
`Stl2StepFusion.py` and `Stl2StepFusion.manifest`) into Fusion's add-in
directory:

- Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`
- macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion/API/AddIns`

Alternatively, open **Utilities → Scripts and Add-Ins**, click **+** beside
**My Add-Ins**, and select the `Stl2StepFusion` folder. Select the add-in in the
list and click **Run**. Selecting the `.py` file itself does not install this
add-in correctly.

Make the engine available in one of these locations, checked in order:

1. The path in the `STL2STEP_EXECUTABLE` environment variable.
2. A platform-specific path inside `Stl2StepFusion/bin/`:
   - `windows-x86_64/stl2step.exe`
   - `macos-arm64/stl2step`
   - `macos-x86_64/stl2step`
3. `stl2step` on `PATH`.

For a reproducible Windows bundle, build the CLI and run this from the
repository root:

```powershell
cmake --build build --config Release
.\scripts\package-fusion-windows.ps1
```

The script copies `stl2step.exe` and the OCCT runtime DLLs into
`Stl2StepFusion\bin\windows-x86_64`. The executable and its DLLs are kept
together, so the add-in does not depend on OCCT or a machine-specific PATH.
If OCCT cannot be inferred from `CMakeCache.txt`, pass its runtime directory
explicitly with `-OcctBin C:\path\to\occt\bin`.

With the add-in running and a Design document open, switch to the **UTILITIES**
tab, open **ADD-INS**, and choose **STL to STEP Solid**. The toolbar command is
not available until the add-in has been run from the Scripts and Add-Ins
dialog.

The release manifest enables **Run on Startup**, so after the first install and
Fusion restart the command is available automatically. The Scripts and Add-Ins
startup toggle controls future launches; it is not the immediate Run/Stop
control.

## Current behavior

- Prompts for an STL file.
- Prompts whether the unitless STL coordinates represent millimetres or inches.
- Prompts for TrueForm or Verbatim conversion mode.
- Runs the selected mode with `--quiet --no-verify` on a worker thread.
- Treats converter exit codes 0 and 2 as a produced STEP file.
- Imports the STEP only after the Fusion command has ended, using a custom event
  on Fusion's main thread.
- Shows a progress dialog while converting, then key `RESULT` statistics and
  warnings after import.
- Removes the temporary conversion directory after a successful import.

The imported STEP is direct B-Rep geometry. This does not reconstruct Fusion
sketches, constraints, dimensions, or timeline features.
