# Output contract and legacy commands

Read for custom naming, output-contract diagnosis, or single-option processing.
Normal runs use `run_icons.py`; it owns names, salts, validation, and publication.

## Required assets

Each accepted option has a 1024×1024 master, exact 29×29, 30×23, and 30×18 PNG
canvases, and a true ICO with 16, 20, 24, 32, 40, 48, 64, 128, and 256 pixel
frames. Sources are square; reject non-square art. Resizing is proportional,
centered, LANCZOS, and uncropped. Background is white by default or transparent
when requested. Preserve enclosed white foreground when isolating border white.

Render every PNG and ICO frame from the isolated RGBA artwork before applying
its final background. Independent ICO frames use the same one-pixel-clear fit as
previews, then are embedded as PNG bytes without another resize. White frames
have exact opaque-white corners; transparent frames have zero-alpha corners.
Do not regenerate artwork for an encoding or background-compositing defect.

## Names and manifests

Normalize a short Title Case summary (normally two to five words, max 40 chars).
The naming helper handles Windows-invalid characters, whitespace, trailing
punctuation, and reserved device names. Assign each visually accepted option a
unique ten-character lowercase-alphanumeric salt; keep it through processing
retries and reuse it for every file in that option:

```text
[summaryName] option [n] [width]x[height] [salt].png
[summaryName] option [n] [salt].ico
```

The runner stages the complete set outside final output, decodes every ICO frame,
validates geometry, modes, dimensions, backgrounds, names and salts, then writes
file hashes plus actual visual-QA evidence in the manifest. Publication refuses
existing files and rolls back only newly created files on error. Prior icon sets
are preserved. Use `manifest.json` when available; otherwise the runner writes
`manifest [run_id].json`. Logs and previews stay in the owned workspace. Do not
create a ZIP unless requested.

## Legacy helpers

`process_icons.py` accepts `--staging-root` outside output. It stages and validates
one option before publication. `--metadata <FILE>` saves full metadata; stdout is
a summary unless `--verbose` is requested. `validate_icon_assets.py --manifest`
prints counts and failures; `--report <FILE>` saves full diagnostics, and
`--verbose` also prints all checks. Use these helpers only for targeted work.
Do not patch Python's temporary-directory implementation to redirect staging.
