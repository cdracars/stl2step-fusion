# Fusion 360 smoke test

Use this checklist against the installed release ZIP, not only the source
checkout. It verifies the host integration, packaged engine, and user-facing
behavior together.

## Setup

- [ ] Start Fusion 360 with a blank or disposable Design document.
- [ ] Install the complete release ZIP into the Fusion AddIns folder.
- [ ] Confirm the add-in loads without an error dialog.
- [ ] Confirm the add-in package contains `bin/windows-x86_64/stl2step.exe`
      and its runtime DLLs.
- [ ] Prepare one small, closed STL and one larger or open-shell STL.

## Happy path

- [ ] Open the command and confirm the defaults are millimetres and TrueForm.
- [ ] Convert the closed STL and confirm Fusion remains responsive.
- [ ] Confirm a new Fusion document opens and the source document is unchanged.
- [ ] Confirm the completion summary includes output name, geometry counts,
      elapsed time, and engine version.
- [ ] Close the result and repeat the command.
- [ ] Confirm the previous units and conversion mode are remembered.

## Modes and warnings

- [ ] Convert with Verbatim and confirm the summary identifies Verbatim mode.
- [ ] Convert the open-shell STL and confirm warning text is visible when the
      engine reports a usable result with exit code `2`.
- [ ] Confirm a failed conversion shows a concise error and does not open a
      partial result.

## Cancellation and recovery

- [ ] Start a conversion large enough to observe the progress dialog.
- [ ] Click Cancel and confirm the child process stops and Fusion remains usable.
- [ ] Confirm cancellation does not leave a stale busy state on the next run.
- [ ] If import fails after conversion, confirm the generated STEP path is
      shown and the retained file can be opened manually.
- [ ] Stop or unload the add-in during conversion and confirm the native engine
      process exits.

## Release checks

- [ ] Test from a clean user profile or machine without a source checkout.
- [ ] Confirm no Python package, PATH change, or separately installed OCCT is
      required.
- [ ] Record Fusion version, Windows version, STL characteristics, mode, and
      elapsed time with any issue report.

