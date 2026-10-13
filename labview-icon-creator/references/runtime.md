# Batch runtime

Read when executing an icon run. Use the recorded absolute Python executable in
all commands. On PowerShell, invoke it with `& 'C:\path\python.exe'`; on POSIX
use its quoted path directly. `<PY>`, `<SKILL>`, and `<RUN>` below are placeholders.
Use shell-appropriate quoting and avoid inferred filenames.

## Initialize once

Write a small `plan.json` in an allowed temporary location:

```json
{
  "request": "the user's icon concept",
  "summary_name": "Concise Title",
  "background_mode": "white",
  "concepts": [
    {"concept_id": "unique-id", "concept_summary": "Short visual description",
     "signature": {"metaphor": "...", "objects": "...", "cue": "...",
                   "composition": "...", "orientation": "..."},
     "prompt": "One standalone square PNG icon; ..."}
  ]
}
```

Supply exactly five concepts. Semantic preflight belongs to the model; different
IDs alone do not establish distinctness.

```text
<PY> <SKILL>/scripts/run_icons.py init --plan <PLAN> --output-dir <OUTPUT>
```

This checks writable output/work locations and records the runtime. The default
work parent is OS temp. If it is unavailable, use `--work-root <WRITABLE_PARENT>`
outside the final output directory, such as this chat's visualization workspace.
The owned-directory helper inherits parent access on Windows, including Python
3.14 managed sandboxes, while retaining private mode 0700 on POSIX.
Do not monkey-patch temporary-directory behavior or retry unchanged permissions.
The returned `run_file` is `<RUN>`; keep it for revisions and recovery.

## Generate and save

`run_icons.py jobs --run-file <RUN>` returns ready jobs with explicit destination
paths, interpreter, saver, background, and concurrency. Completed source files
are excluded. Each candidate is its own image-generation call. Concurrency 2
reduces elapsed time, not total image usage; use 1 if the provider cannot safely
run concurrent calls. Tool waits remain subject to the host's limits.

Read `scripts/generate_candidates.js` once through the shell and store its source
inside functions.exec without printing it. It is a function expression usable as
`new Function("return (" + source + ")")()`. Pass the jobs JSON and dependencies:

```javascript
const receipts = await generate(config, {
  tools, notify, showResult: generatedImage,
  loadResult: id => load("icon-result-" + id),
  retainResult: (id, result) => store("icon-result-" + id, result)
});
text(receipts);
```

Use a run-specific prefix for those store keys when multiple runs share a chat.
The adapter uses one PTY stdin process and one bulk payload write per data URL
(plus an explicit Enter key on Windows), with echo disabled; it does not
put base64 in shell commands or print image payloads. If the tool supplies a
local source, supply `local_source` on its job instead; `save_source.py --source`
validates and copies the bytes. Tool output formats vary: use only actual
returned artifacts, not guessed paths. After a transfer error, rerun the affected
job with its retained result or local artifact; do not generate another image.
A runtime without writable stdin or local artifacts requires a supported
transport route before further generation can continue; retain the generated result and report
this limitation.

## Preview, review, and retry

```text
<PY> <SKILL>/scripts/run_icons.py previews --run-file <RUN>
```

Inspect each full-size source (or generation result) and the returned sheet.
Record one review JSON with candidate-specific results for `source`, `29x29`,
`30x23`, `30x18`, and `16x16`. Each has `result` and `evidence`; failed entries
also need `rule_id`, with `correction` and `cause` when observed. Example shape:

```json
{
  "candidates": [
    {"candidate_id": "candidate-01", "qa": {
      "source": {"result": "PASS", "evidence": "Observed silhouette, clearance and correct action."},
      "29x29": {"result": "PASS", "evidence": "Observed main object and action remain separate."},
      "30x23": {"result": "PASS", "evidence": "Observed functional cue remains recognizable."},
      "30x18": {"result": "PASS", "evidence": "Observed essential outputs remain separate."},
      "16x16": {"result": "WARN", "evidence": "Dominant parsing cue survives; secondary dots merge."}
    }}
  ],
  "distinctness": {"result": "PASS", "candidate_ids": ["candidate-01"],
                   "evidence": "Explain the visible metaphors/compositions of the actual selected set."}
}
```

The example is a schema, not a prewritten approval: assess actual images. Review
all five candidates and include the entire selected set in the distinctness
record. Source assessment covers every applicable VIS rule. Per-size assessments
cover the applicable SMALL rules; record actual failed rules and sizes.

```text
<PY> <SKILL>/scripts/run_icons.py review --run-file <RUN> --review-file <REVIEW>
<PY> <SKILL>/scripts/run_icons.py retry --run-file <RUN> --candidate-id <FAILED_ID> --prompt <CORRECTION>
```

After three attempts for a concept, provide `--replacement-plan <JSON>` containing
a different concept's ID, signature, summary, and prompt. Retry creates a new
candidate/file, preserving evidence and previous sources. Generate pending jobs,
rebuild the sheet, and update the affected reviews plus final distinctness.
Never retry accepted art for a deterministic processing failure.

## Publish and clean owned files

```text
<PY> <SKILL>/scripts/run_icons.py finalize --run-file <RUN>
<PY> <SKILL>/scripts/run_icons.py cleanup --run-file <RUN>
```

Finalize validates all staged assets, writes hashes and visual approvals, and
publishes only after package validation. An existing `manifest.json` is preserved;
subsequent runs receive `manifest <run_id>.json`. A failed publication rolls back
only files created by that attempt; sources and salts remain available for retry.
`validation.json` keeps full diagnostics in the owned workspace; stdout reports
counts and failures. Repeated finalize verifies an already published package.
Cleanup requires the ownership marker and a successful publication. It removes
only that temporary workspace, never earlier deliverables or user files. Keep the
workspace while diagnosing a failure. `status` returns compact run/runtime data.
At 20 generated candidates, `--allow-shortfall` publishes compliant options and
records the exact shortfall; it cannot bypass the limit or visual QA.
