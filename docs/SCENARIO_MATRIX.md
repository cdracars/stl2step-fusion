# Cross-CAD scenario matrix

This matrix is the shared behavioral target for the FreeCAD and Fusion 360
wrappers. The UI and host APIs may differ, but the outcomes should match.

| Scenario | Expected outcome |
| --- | --- |
| First run | Millimetres and TrueForm are selected by default. |
| Changed options | Units and mode are remembered for the next run. |
| Exit code 0 | STEP imports as a new CAD document; source remains unchanged. |
| Exit code 2 with usable STEP | Import succeeds and warnings are visible. |
| Exit code 1 or other failure | Clear error; no partial result is opened. |
| Malformed/missing RESULT | Clear engine error with stderr when available. |
| Success without STEP output | Clear missing-output error. |
| User cancellation | Child process stops, temporary files are cleaned, host remains usable. |
| Import failure after conversion | Generated STEP is retained and its path is shown. |
| Host shutdown during conversion | Engine process is signaled to stop; no orphan conversion remains. |
| Clean installation | Release ZIP works without a source checkout, Python package, PATH change, or separate OCCT install. |

The manual Fusion execution steps are in
[`FUSION_SMOKE_TEST.md`](FUSION_SMOKE_TEST.md).
