# Engine contract

This repository is a Fusion 360 host wrapper around the external
[`stl2step`](https://github.com/BlinkingSun/stl2step) executable. The executable
is not a Python dependency and is not committed to this source repository.

## Supported behavior

- TrueForm conversion is the default and recovers analytic geometry where
  possible.
- Verbatim conversion preserves faceted STL surfaces.
- STL units default to millimetres; inches are also supported.
- Conversion runs asynchronously so Fusion remains responsive.
- Users can cancel an active conversion.
- Exit code `0` is success. Exit code `2` is success with warnings when a
  usable STEP file exists. Other exit codes are failures.
- The final `RESULT` record is authoritative; malformed or missing result data
  is an error.
- A reported success without a STEP file is an error.
- Successful output is opened as a new Fusion document. The source document is
  not modified.
- The host communicates conversion and import as distinct user-facing phases.
- Temporary files are removed after successful import or cancellation. If
  conversion succeeds but Fusion cannot import the result, the STEP file is
  retained and its path is shown for recovery.
- Unloading the add-in signals cancellation so the native engine process does
  not remain running after Fusion removes the add-in UI.

## Cross-CAD parity

The FreeCAD wrapper follows the same behavior contract. User-facing terms,
defaults, outcome states, warning semantics, and cleanup guarantees should
remain equivalent. The command panel, progress UI, threading/event model, and
document-import mechanism remain native to Fusion.

The shared project context contains the canonical parity model and scenario
matrix for both wrappers.

## Release provenance

The pinned engine release and checksum are defined in
[`config/engine-release.json`](config/engine-release.json). Release packaging
vendors that exact asset and includes the upstream license and runtime notices.
