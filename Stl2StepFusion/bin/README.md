# Engine bundles

Release packaging places the `stl2step` executable and its OCCT runtime DLLs
under one of these directories:

- `windows-x86_64/`
- `macos-arm64/`
- `macos-x86_64/`

For Windows, use `scripts/package-fusion-windows.ps1` from the repository root.
Keeping the DLLs beside the executable is required for a portable add-in; do
not rely on the developer machine's OCCT PATH. For development, setting
`STL2STEP_EXECUTABLE` is usually faster than copying a build here.
