# STL to STEP Solid for Autodesk Fusion 360

This project packages the open-source [`stl2step` engine](https://github.com/cdracars/stl2step)
as a standalone Autodesk Fusion 360 add-in. It lets Fusion users select an STL,
convert it to a STEP B-Rep solid, and open the result in a new Fusion document.
The currently open Fusion document is not modified.

## Install on Windows

1. Download this repository as a ZIP using **Code → Download ZIP** on GitHub.

2. Extract the ZIP. Open the extracted folder, then open its `Stl2StepFusion`
   folder. This is the folder that contains `Stl2StepFusion.manifest`.

3. Copy that complete `Stl2StepFusion` folder to:

   `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`

   You can paste the path into File Explorer’s address bar. The final layout
   must look like this:

   ```text
   %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\Stl2StepFusion\
       Stl2StepFusion.manifest
       Stl2StepFusion.py
       engine.py
       bin\windows-x86_64\stl2step.exe
       bin\windows-x86_64\*.dll
   ```

4. Start or restart Fusion 360.

5. Open **Utilities → Scripts and Add-Ins** and select the **Add-Ins** tab.
   Select **Stl2StepFusion**, click **Run**, and check **Run on Startup**.

6. Close the Scripts and Add-Ins window. In the **Utilities** workspace, click
   **STL to STEP Solid**.

The add-in includes the converter and required OCCT runtime DLLs. No separate
Python, OpenCASCADE, PATH setting, or build step is required.

## Using the add-in

1. Click **STL to STEP Solid**.
2. Choose an `.stl` file.
3. Choose the STL units: millimetres or inches.
4. Choose a conversion mode:
   - **TrueForm** (recommended) recovers editable planes, cylinders, and
     fillets where possible.
   - **Verbatim** preserves the original faceted STL surfaces and is usually
     faster.
5. Wait for conversion to finish. The STEP opens as a new Fusion document.

For large meshes, conversion can take several minutes. The progress dialog’s
**Run in background** button lets Fusion remain usable while conversion runs;
completion is reported in Fusion’s status bar and result dialog.

## Troubleshooting

- If **Stl2StepFusion** is not listed, confirm that you copied the inner
  `Stl2StepFusion` folder—the folder containing the manifest—not the outer ZIP
  folder and not the `.py` file by itself.
- If the toolbar command is missing, open Scripts and Add-Ins, select the
  add-in, and click **Run** once. Then restart Fusion with **Run on Startup**
  checked.
- If Windows reports a missing DLL, confirm that the entire `bin\windows-x86_64`
  folder was copied, including all DLL files.

## Relationship to stl2step

The conversion engine is maintained in the separate
[stl2step repository](https://github.com/cdracars/stl2step). This Fusion repo
contains a packaged Windows build of that engine so end users do not need to
build it themselves.

The imported result is direct B-Rep geometry. It does not recreate Fusion
sketches, constraints, dimensions, or timeline features.

## Engine updates

This repository checks the upstream `stl2step` releases weekly. When a newer
Windows engine is available, GitHub Actions downloads and validates it, then
publishes the updated bundle to the `automation/update-engine` branch for review.
The Fusion add-in code is not changed by that update. Merge that branch into
`main` when the updated engine has been tested.
