---
name: labview-icon-creator
description: Generate five distinct, QA-validated LabVIEW VI icon options from a short concept, with exact-size PNG derivatives, multi-resolution Windows ICO files, a manifest, and failure-driven lessons learned. Use for LabVIEW icon artwork or LabVIEW VI icon-set requests; do not use for general illustrations or vector-only logo work.
---

# LabVIEW Icon Creator

Create practical software icons whose real design target is 18–30 pixels. The
normal result is five independently generated and accepted source PNGs, three
resized PNGs and one ICO per option, plus `manifest.json`, all written directly
to the user's current working directory. Do not create a ZIP unless requested.

## Preflight

Before image generation:

1. Confirm an independent raster image-generation tool is callable.
2. Confirm generated images can be visually inspected with image/vision tools.
3. Run `python3 -c "import PIL; print(PIL.__version__)"` and confirm Python 3 and
   Pillow are available.

If any capability is absent, stop before generation and name the missing
capability. Do not substitute text-only concepts, placeholders, ASCII art, or
unconvertible images while claiming completion.

## Run workflow

1. Read [references/style-guide.md](references/style-guide.md), then interpret
   the request. Ask a question only when ambiguity or conflicting constraints
   would materially change the icons.
2. Derive a two-to-five-word `summaryName` and normalize it with
   `scripts/naming.py`. Plan exactly five meaningfully different concepts for
   the same function. Reject weak or duplicate concepts before generation;
   preflight rejections do not count as QA failures.
3. Create a temporary working directory. Generate every candidate as its own
   full-resolution square raster image—normally 1024×1024 PNG. Never generate
   a grid, montage, contact sheet, or other multi-option source image.
4. Read [references/qa-guide.md](references/qa-guide.md). Inspect every generated
   source and scripted 29×29, 30×23, 30×18, and 16×16 preview. Record explicit
   `PASS`, `FAIL`, `WARN`, or `N/A` results. A mandatory `FAIL` rejects the
   candidate; do not weaken a rule to finish the run.
5. Give a planned concept at most three generated attempts. After three failed
   attempts, retire it and plan a different visual approach. Stop generation at
   20 total candidates. Record each post-generation, processing, or final-file
   failure as JSON Lines using the fields in the QA guide. Use corrective
   prompts based only on observed defects and regenerate only the affected
   concept.
6. Assign a unique permanent ten-character salt only after a source passes
   full-size and small-size visual QA. Reuse that salt for all files belonging
   to the accepted option. Do not assign final salts to rejected candidates.
7. Read [references/naming-and-output.md](references/naming-and-output.md). Run
   `scripts/process_icons.py` for each accepted source. Run
   `scripts/validate_icon_assets.py` before presenting any deliverable. Keep
   rejected sources, transient previews, and raw QA logs in the temporary area.
8. Use `scripts/manifest.py` to write `manifest.json` containing only accepted
   options and SHA-256 hashes. If any qualifying failure occurred, read
   [references/lessons-learned-guide.md](references/lessons-learned-guide.md)
   and run `scripts/lessons_learned.py`; otherwise create no lessons file.
9. Remove disposable temporary artifacts. Present only accepted options with a
   short concept summary and links to their files. Do not expose internal logs
   unless requested.

If the 20-candidate limit is reached before five options pass, return the
compliant options already completed, state the exact shortfall, create the
lessons-learned report, and do not claim full success.

## Script conventions

Run helpers from this skill directory or use their absolute paths. Their CLI
help documents arguments. The default output directory is the caller's current
working directory. Treat script validation as complementary to—not a
replacement for—visual inspection.
