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
