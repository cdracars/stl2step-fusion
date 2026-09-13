# Engine bundles

Release packaging places the `stl2step` executable and its OCCT runtime DLLs
under one of these directories:

- `windows-x86_64/`
- `macos-arm64/`
- `macos-x86_64/`

The repository currently ships the Windows bundle directly; there is no local
packaging script. Release automation replaces this directory with the
validated Windows asset from the upstream release.
Keeping the DLLs beside the executable is required for a portable add-in; do
not rely on the developer machine's OCCT PATH. For development, setting
`STL2STEP_EXECUTABLE` is usually faster than copying a build here.
