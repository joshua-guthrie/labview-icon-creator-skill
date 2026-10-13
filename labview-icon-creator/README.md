# LabVIEW Icon Creator

This Codex Agent Skill turns a short LabVIEW VI icon request into five distinct,
visually inspected options and 25 validated icon files. Each accepted option
has a 1024×1024 master PNG, 29×29, 30×23, and 30×18 PNG derivatives, and a true
multi-resolution Windows ICO.

Runtime requirements are Python 3, Pillow, a raster image-generation capability,
and image/vision inspection. Install Python dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

Run deterministic tests without any live image generation:

```bash
python3 -m unittest discover -s tests -v
```

Invoke the installed skill with a request such as:

```text
Use $labview-icon-creator to create an icon for adding a driver to the system.
```

Final accepted assets are written directly to the current working directory.
No ZIP is created unless explicitly requested.


The normal execution path is the batch runner documented in
[references/runtime.md](references/runtime.md). It records the chosen Python,
manages sources and visual reviews, renders a shared QA sheet, and publishes a
validated package with compact diagnostics. ICO frames match the reviewed
renderer exactly. Earlier deliverables are preserved.

On Windows, a working `python`, `py -3`, or bundled interpreter is sufficient;
WSL is optional. Image transfer and bounded generation concurrency are provided
by `scripts/generate_candidates.js`. The adapter uses the active tool runtime;
Node.js is only needed for its offline development tests:

```text
node tests/test_generate_candidates.cjs
```

Use a fresh chat for an unrelated icon set if the existing conversation is long.
Keep revisions to the same set in their recorded run. Image-generation and
semantic review remain model responsibilities; the offline suite does not
measure live generation quality, speed, or account usage.
