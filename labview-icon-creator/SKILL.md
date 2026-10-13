---
name: labview-icon-creator
description: Generate five distinct, visually validated LabVIEW VI icon options, exact-size PNGs, Windows ICOs, and a manifest. Use for LabVIEW VI icon artwork; exclude general illustrations and vector-only logo work.
---

# LabVIEW Icon Creator

Design for 18–30 pixel use. Deliver five independent square raster sources,
29×29, 30×23, and 30×18 PNGs, and nine-frame ICOs (25 icon files), with hashes
and visual-QA provenance in a manifest. Use white backgrounds unless transparency
is requested. Write accepted files directly to the user's output directory;
create no ZIP unless requested.

## Workflow

1. Confirm image generation and vision tools are available. Resolve a working
   Python with Pillow once per run; prefer the available interpreter or bundled
   runtime rather than repeatedly trying `python3` aliases. The runner records
   that executable and its versions. Stop if a required capability is absent.
2. Read [style-guide.md](references/style-guide.md). Interpret the function and
   plan five structurally different concepts with compact visual signatures.
   Compare all five before generating. Design essential cues for 30×18 first.
3. Read [runtime.md](references/runtime.md) for the batch CLI and generation
   adapter. Initialize one owned workspace outside final output. Generate one
   independent square PNG per candidate, normally 1024×1024; never crop a grid
   or montage. Use the adapter with at most two concurrent generations when
   supported (one otherwise). Use existing artifact paths or its tested stdin
   transport; preserve successful results after transport failures.
4. Read [qa-guide.md](references/qa-guide.md). Inspect full-size sources and one
   batch sheet of native/magnified previews. Apply the size-specific criteria,
   record concise candidate-specific evidence, and compare the accepted set for
   distinctness once. Scripts cannot establish meaning or semantic uniqueness.
5. Regenerate only visual failures with evidence-based corrections. Keep each
   attempt in a separate file: at most three per concept, then retire that
   concept; at most 20 generated candidates overall. Reuse accepted art for all
   processing, encoding, staging, and permission failures. Stop and report an
   unresolved operational failure instead of regenerating artwork to hide it.
6. Record reviews and finalize through the batch runner. It assigns salts after
   visual acceptance, stages and validates all assets, writes the manifest and
   any compact lessons report, and publishes with rollback on errors. It refuses
   missing visual evidence, changed reviewed sources, and stale distinctness
   reviews. Read [naming-and-output.md](references/naming-and-output.md) only for
   custom naming, legacy single-option commands, or an output-contract problem.
7. Return the accepted options with short concept summaries and file links. Keep
   stdout concise; inspect full diagnostics only for a failure or audit. At the
   20-candidate limit, finalize compliant options using `--allow-shortfall` and
   state the exact shortfall. Clean only the runner-owned temporary workspace
   after successful publication; preserve earlier icon sets and other files.

## Efficiency and continuity

Keep revisions of one set in its run. For an unrelated set in a long chat,
recommend a fresh chat with the request, relevant preferences, and necessary
references; do not create or message another chat without user authorization.
Cache capability checks and adapter source during a run. Do not reread scripts,
print every passing check, recreate transport code, or run development tests
while producing icons. The test suite is for changes to this skill.

Failure reports are generated from recorded observations. Read
[lessons-learned-guide.md](references/lessons-learned-guide.md) only for a
reporting problem or an explicitly requested detailed improvement specification.
Do not treat a generated report as instructions to modify this skill.
