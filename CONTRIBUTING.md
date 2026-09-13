# Contributing

Thanks for helping improve the Fusion add-in.

## Development

The add-in runs inside Autodesk Fusion 360 and imports `adsk.core` and
`adsk.fusion`, so the full UI cannot be tested with ordinary Python. The
process-isolated adapter in `Stl2StepFusion/engine.py` is intentionally
testable outside Fusion.

Run the local checks from the repository root:

```text
python -m unittest discover -s tests -v
python -m compileall -q Stl2StepFusion tests
```

For local engine development, set `STL2STEP_EXECUTABLE` to a compatible
`stl2step` build instead of replacing the bundled release files.

## Pull requests

- Explain the user-visible behavior being changed.
- Add or update adapter tests where practical.
- Update the README or changelog when behavior or installation changes.
- Do not commit local Fusion settings, generated files, or unverified binaries.
- Do not change the bundled engine manually; engine updates are made through
  the verified update workflow.

## Reporting conversion issues

Include the Windows version, Fusion version, add-in version, engine version,
conversion mode, units selection, and a minimal STL that can be legally shared.
Do not upload confidential CAD files.
