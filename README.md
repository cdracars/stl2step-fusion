# STL to STEP Solid for Autodesk Fusion 360

This project packages the open-source [`stl2step` engine](https://github.com/BlinkingSun/stl2step)
as a standalone Autodesk Fusion 360 add-in. It lets Fusion users select an STL,
convert it to a STEP B-Rep solid, and open the result in a new Fusion document.
The currently open Fusion document is not modified.

## Requirements and compatibility

- Autodesk Fusion 360 for Windows with permission to install add-ins.
- Windows x64. macOS is not currently packaged or supported by this add-in.
- A Fusion **Design** document must be open when the command is started.

## Install on Windows

1. Download the latest Windows release ZIP from the repository’s
   [Releases page](https://github.com/cdracars/stl2step-fusion/releases).
   The source ZIP from **Code → Download ZIP** does not include the native
   engine bundle and is intended for development only.

2. Extract the ZIP. Open the extracted folder, then open its `Stl2StepFusion`
   folder. This is the folder that contains `Stl2StepFusion.manifest`.

3. Copy that complete `Stl2StepFusion` folder to:

   `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns`

   You can paste the path into File Explorer’s address bar. The release
   archive’s layout must look like this:

   ```text
   %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\Stl2StepFusion\
       Stl2StepFusion.manifest
       Stl2StepFusion.py
       engine.py
       bin\windows-x86_64\stl2step.exe
       bin\windows-x86_64\*.dll
   LICENSE.stl2step
   THIRD_PARTY_NOTICES.md
   licenses\
   ```

4. Start or restart Fusion 360.

5. Open **Utilities → Scripts and Add-Ins** and select the **Add-Ins** tab.
   Select **Stl2StepFusion**, click **Run**, and check **Run on Startup**.

6. Close the Scripts and Add-Ins window. In the **Utilities** workspace, click
   **STL to STEP Solid**.

The release archive includes the converter and required OCCT runtime DLLs. No
separate Python, OpenCASCADE, PATH setting, or build step is required. The
source checkout intentionally does not contain native engine binaries.

## Using the add-in

1. Click **STL to STEP Solid**.
2. Choose the STL units: millimetres or inches.
3. Choose a conversion mode:
   - **TrueForm** (recommended) recovers analytic planes, cylinders, and
     fillets where possible.
   - **Verbatim** preserves the original faceted STL surfaces and is usually
     faster.
4. Click **OK**, then choose an `.stl` file.
5. Wait for conversion to finish. The STEP opens as a new Fusion document.

For large meshes, conversion can take several minutes. The progress dialog’s
**Cancel** button stops the converter and cleans up its temporary files;
completion or cancellation is reported in Fusion’s status bar and result
dialog.

## Known limitations

- STL units are not reliably encoded in the STL format, so the units choice is
  manual. Choosing the wrong units changes the imported size.
- The result is direct B-Rep geometry, not a parametric Fusion feature tree.
- Open, self-intersecting, or very large meshes may produce open shells, take a
  long time, or fail to import.
- The progress percentage is unavailable. **Cancel** stops the converter and
  cleans up its temporary files.

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
[stl2step repository](https://github.com/BlinkingSun/stl2step). This Fusion repo
contains a packaged Windows build of that engine so end users do not need to
build it themselves.

The imported result is direct B-Rep geometry. It does not recreate Fusion
sketches, constraints, dimensions, or timeline features.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the bundled engine,
OCCT, runtime libraries, and their licensing requirements.
The license-text checklist for binary releases is in [licenses/README.md](licenses/README.md).

For contributors, see [CONTRIBUTING.md](CONTRIBUTING.md). Security issues
should follow [SECURITY.md](SECURITY.md). Version history is in
[CHANGELOG.md](CHANGELOG.md), and tagged releases include a SHA-256 checksum.
The engine behavior contract is documented in
[ENGINE_CONTRACT.md](ENGINE_CONTRACT.md).
The manual Fusion validation checklist is in
[docs/FUSION_SMOKE_TEST.md](docs/FUSION_SMOKE_TEST.md).
The cross-CAD scenario matrix is in
[docs/SCENARIO_MATRIX.md](docs/SCENARIO_MATRIX.md).

## Engine updates

This repository checks the upstream [`stl2step`](https://github.com/BlinkingSun/stl2step)
releases weekly. When a newer
Windows engine is available, GitHub Actions downloads and validates it, then
opens a pull request containing the updated bundle. The PR is configured to
auto-merge after the workflow succeeds and closes automatically. The Fusion
add-in code is not changed by that update.

The current engine provenance and SHA-256 pin are recorded in
[config/engine-release.json](config/engine-release.json). Updates are accepted only when the
upstream release manifest and checksum file agree with the downloaded asset.

