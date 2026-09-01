# LabVIEW Icon Creator skill

A production-oriented Codex skill that creates five distinct LabVIEW VI icon
options, checks their legibility at LabVIEW sizes, and produces exact-size PNG
derivatives plus multi-resolution Windows ICO files.

The installable skill package is in [`labview-icon-creator/`](labview-icon-creator/).
Its deterministic image-processing and validation code is covered by offline
tests; live image generation is intentionally a runtime Codex capability.

Run the test suite from the repository root:

```bash
python3 -m unittest discover -s labview-icon-creator/tests -v
```
