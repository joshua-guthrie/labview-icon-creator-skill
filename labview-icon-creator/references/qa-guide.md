# QA guide

Read this reference while reviewing generated sources and small previews.
Automated metrics support but never replace visual inspection.

## Result model

Every applicable check has a stable ID, severity, description, result, observed
evidence, and—when measurable—a value and threshold. Results are:

- `PASS`: requirement satisfied.
- `FAIL`: mandatory requirement not satisfied; reject the candidate.
- `WARN`: non-blocking concern worth recording.
- `N/A`: rule does not apply.

Preferred guidance and approximate ranges are not automatic failures when the
artwork remains safe and readable.

## Source-image rules

| Rule | Mandatory failure condition |
|---|---|
| `VIS-SEM-001` Semantic correctness | Wrong principal object, opposite action, materially different function, or likely common misreading. |
| `VIS-CONCEPT-002` Concept fidelity | Image no longer represents its planned concept. |
| `VIS-SIMPLE-003` Visual simplicity | Excess objects, repetition, texture, decorative detail, or illustration-like scene. |
| `VIS-DETAIL-004` Small-feature risk | Essential meaning depends on thin lines, narrow gaps, tiny labels/dots/teeth, or buried symbols. |
| `VIS-MARGIN-005` Edge clearance | Important artwork is cramped, touches an edge, or risks clipping. A safely readable borderline metric may be `WARN`. |
| `VIS-OCCUPANCY-006` Subject occupancy | Obviously too small to survive or too large for the canvas. The normal target is 55–85%. |
| `VIS-CONTRAST-007` Contrast | Essential foreground, adjacent shapes, or action cue cannot be clearly separated. |
| `VIS-GRADIENT-008` Gradient | Gradient or shading materially reduces contrast, obscures required geometry, or introduces small-size noise; antialiasing is allowed. |
| `VIS-BACKGROUND-009` Background | Outer background does not match the run's declared mode—pure white by default or transparent when requested—or a scene, texture, shadow, halo, or effect reduces clarity. |
| `VIS-TEXT-010` Text | Unrequested letters, labels, pseudo-text, or prominent text-like artifacts. Requested text is allowed, but fails if it is malformed or too small to be intentionally legible. |
| `VIS-ARTIFACT-011` Artifacts | Malformed/duplicate geometry, debris, halos, corruption, or broken generated shapes. |
| `VIS-DISTINCT-012` Cross-option distinctness | Candidate substantially duplicates an accepted option; replace at least one. |

## Small-size rules

Create temporary previews at native 29×29, 30×23, 30×18, and 16×16 on the
selected final background. Use `scripts/preview_sheet.py --background white` by
default or `--background transparent` when requested to include native previews
and 10×–16× nearest-neighbor enlargements. Never use the sheet as source artwork.

| Rule | Mandatory failure condition |
|---|---|
| `SMALL-RECOG-001` Recognition | Main object/action is materially ambiguous at any required PNG size. |
| `SMALL-16-002` 16×16 stress | Dominant silhouette becomes an unidentifiable blob. Secondary-detail loss is acceptable. |
| `SMALL-LINE-003` Line survival | A required line/separator disappears and changes meaning. |
| `SMALL-SHAPE-004` Shape separation | Required elements merge and alter meaning. |
| `SMALL-CROWD-005` Pixel crowding | Reduced icon is muddy, noisy, or excessively crowded. |
| `SMALL-ACTION-006` Action survival | A required action/status symbol disappears or becomes ambiguous. |
| `SMALL-TEXT-007` Text legibility | Requested text becomes unreadable, merges, or changes character identity at any required size. |

## Failure handling and log

For a failure, record observed evidence and a concise technical cause hypothesis,
not hidden reasoning. Create a corrective prompt aimed at the failed rule; do not
redesign accepted options. Examples: enlarge and thicken a disappearing action
symbol, remove secondary detail, restore about 10% margin, or switch to a truly
different metaphor/composition.

Write one JSON object per line with these fields when available:

```text
run_id, timestamp, skill_version, request_summary, option_number, concept_id,
attempt_number, candidate_id, qa_stage, rule_id, severity, result,
observed_problem, measured_value, threshold, likely_cause_hypothesis,
corrective_instruction, retry_result
```

Qualifying `FAIL` stages are generated-source visual QA, small-size visual QA,
scripted processing, final PNG validation, and final ICO validation. A concept
preflight rejection does not qualify.
