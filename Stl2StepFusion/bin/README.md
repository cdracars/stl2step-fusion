# Engine bundles

Release packaging places the `stl2step` executable and its OCCT runtime DLLs
under one of these directories:

- `windows-x86_64/`
- `macos-arm64/`
- `macos-x86_64/`

Engine binaries are intentionally not committed to source. Release and CI
automation downloads the exact release recorded in
`config/engine-release.json`, verifies the upstream manifest and SHA-256, and
places the validated files here during packaging.
Keeping the DLLs beside the executable is required for a portable add-in; do
not rely on the developer machine's OCCT PATH. For development, setting
`STL2STEP_EXECUTABLE` is usually faster than copying a build here.
